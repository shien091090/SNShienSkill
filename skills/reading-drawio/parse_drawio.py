#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析 .drawio / .xml / .drawio.png / .drawio.svg，輸出節點、連線、結構檢查。

用法：
    python parse_drawio.py <檔案> [--out 輸出.txt] [--json 輸出.json]

預設把報告寫成 UTF-8 檔案（Windows 主控台是 cp950，直接 print 中文會變亂碼或
UnicodeEncodeError）。寫完用 `cat` 讀那個檔，不要靠 python 的 stdout。

處理了五個容易踩的雷，細節見同目錄 SKILL.md：
  1. 壓縮存檔（deflate+base64）自動解開
  2. <object> 包裝的節點（自訂屬性住在這裡）
  3. 連線標籤是 parent=<edge id> 的子 vertex，不是獨立節點
  4. 脫鉤標籤（style 有 edgeLabel 但 parent=1）
  5. 註解歸屬用「幾何中心 + 歐氏距離」，不可用左上角/曼哈頓
"""
import argparse
import base64
import html
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from collections import defaultdict

ANNOTATION_RE = re.compile(r'^\[(輸入|輸出|驗收條件|用途|備註|說明)\]')


# ---------- 載入（含解壓縮 / 圖片內嵌） ----------

def _inflate(payload):
    """draw.io 壓縮格式：base64 → raw deflate → urldecode。"""
    raw = base64.b64decode(payload)
    try:
        return urllib.parse.unquote(zlib.decompress(raw, -15).decode('utf-8'))
    except zlib.error:
        return urllib.parse.unquote(zlib.decompress(raw).decode('utf-8'))


def load_xml(path):
    """回傳 mxGraphModel 的 ElementTree root，自動處理壓縮與圖片內嵌。"""
    data = open(path, 'rb').read()

    # .drawio.png：XML 藏在 tEXt chunk 的 mxfile 欄位
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        m = re.search(rb'mxfile\x00([^\x00]+)', data) or re.search(rb'mxGraphModel\x00([^\x00]+)', data)
        if not m:
            sys.exit('✗ 這個 PNG 沒有內嵌 draw.io 資料，只能當圖片看')
        data = urllib.parse.unquote(m.group(1).decode('utf-8')).encode('utf-8')

    text = data.decode('utf-8', errors='replace')

    # .drawio.svg：content 屬性帶 mxfile
    if '<svg' in text[:200] and 'content=' in text:
        m = re.search(r'content="([^"]+)"', text)
        if m:
            text = html.unescape(m.group(1))

    root = ET.fromstring(text)

    # 已經是 mxGraphModel
    if root.tag == 'mxGraphModel':
        return root

    # <mxfile><diagram>…  diagram 內可能是壓縮字串，也可能直接是 mxGraphModel
    for dia in root.iter('diagram'):
        inner = dia.find('mxGraphModel')
        if inner is not None:
            return inner
        payload = (dia.text or '').strip()
        if payload:
            return ET.fromstring(_inflate(payload))

    sys.exit('✗ 找不到 mxGraphModel')


# ---------- 解析 ----------

def clean(s):
    if not s:
        return ''
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'<[^>]+>', '', s)          # 清掉 <div> 等殘留 HTML
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


def parse(root):
    """回傳 (nodes, edges, labels, orphan_labels)。id → dict。"""
    verts, edges = {}, {}

    def geom(el):
        g = el.find('mxGeometry')
        f = lambda k: float(g.get(k) or 0) if g is not None else 0.0
        return {'x': f('x'), 'y': f('y'), 'w': f('width'), 'h': f('height')}

    def take(cid, label, attrib, el, extra=None):
        d = dict(geom(el), v=clean(label), style=attrib.get('style') or '',
                 parent=attrib.get('parent'), attrs=extra or {})
        if attrib.get('vertex') == '1':
            verts[cid] = d
        elif attrib.get('edge') == '1':
            edges[cid] = dict(d, source=attrib.get('source'), target=attrib.get('target'))

    # <object> 包裝：label 在 object，vertex/edge 在內層 mxCell，自訂屬性在 object 的其他屬性。
    # 內層 mxCell 沒有 id（id 在 object 上），所以要先記下來，避免下面裸 mxCell 迴圈重複收進去。
    wrapped = set()
    for o in root.iter('object'):
        c = o.find('mxCell')
        if c is None:
            continue
        wrapped.add(id(c))
        extra = {k: v for k, v in o.attrib.items() if k not in ('id', 'label')}
        take(o.attrib.get('id'), o.attrib.get('label'), c.attrib, c, extra)

    # 裸 mxCell
    for c in root.iter('mxCell'):
        if id(c) in wrapped or not c.attrib.get('id'):
            continue
        take(c.attrib.get('id'), c.attrib.get('value'), c.attrib, c)

    # 連線標籤：parent 指向 edge 的 vertex
    labels, orphans = {}, {}
    for i in list(verts):
        d = verts[i]
        if d['parent'] in edges:
            labels[d['parent']] = d['v']
            del verts[i]
        elif 'edgeLabel' in d['style']:
            orphans[i] = d          # 脫鉤：本該掛在線上卻浮在畫布
            del verts[i]

    return verts, edges, labels, orphans


def attribute_annotations(nodes):
    """把 [輸入]/[驗收條件]/[用途] 歸到最近的步驟。用幾何中心 + 歐氏距離。"""
    ann = {i: d for i, d in nodes.items() if ANNOTATION_RE.match(d['v'])}
    steps = {i: d for i, d in nodes.items() if i not in ann and d['v']}
    out = {}
    center = lambda d: (d['x'] + d['w'] / 2, d['y'] + d['h'] / 2)
    for i, d in ann.items():
        cx, cy = center(d)
        ranked = sorted(steps.items(),
                        key=lambda kv: ((center(kv[1])[0] - cx) ** 2 + (center(kv[1])[1] - cy) ** 2) ** .5)
        if not ranked:
            continue
        (b1, d1), (b2, d2) = ranked[0], (ranked[1] if len(ranked) > 1 else ranked[0])
        dist = lambda t: ((center(t)[0] - cx) ** 2 + (center(t)[1] - cy) ** 2) ** .5
        out[i] = {'step': b1, 'dist': dist(d1), 'runner_up': b2, 'runner_up_dist': dist(d2)}
    return ann, steps, out


def validate(nodes, edges, orphans, steps):
    """結構檢查。

    只對「流程節點」(steps = 步驟 + 判斷) 做連通性判斷。
    [輸入]/[驗收條件]/[用途] 註解本來就不連線，算進去會產生大量假孤島與假斷裂。
    """
    nodes = steps
    ind, outd = defaultdict(int), defaultdict(int)
    dangling = []
    for i, e in edges.items():
        if not e['source'] or not e['target']:
            dangling.append(i)
        if e['source'] in nodes:
            outd[e['source']] += 1
        if e['target'] in nodes:
            ind[e['target']] += 1

    # 弱連通分量
    adj = defaultdict(set)
    for e in edges.values():
        if e['source'] in nodes and e['target'] in nodes:
            adj[e['source']].add(e['target'])
            adj[e['target']].add(e['source'])
    seen, comps = set(), []
    for n in nodes:
        if n in seen:
            continue
        stack, comp = [n], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            stack += [y for y in adj[x] if y not in seen]
        comps.append(comp)

    return {
        'in': ind, 'out': outd,
        'dangling': dangling,
        'orphan_labels': list(orphans),
        'isolated': [i for i in nodes if ind[i] == 0 and outd[i] == 0],
        'sources': [i for i in nodes if ind[i] == 0 and outd[i] > 0],
        'sinks': [i for i in nodes if outd[i] == 0 and ind[i] > 0],
        'components': sorted(comps, key=len, reverse=True),
        'dup_names': {v: ids for v, ids in
                      ((v, [i for i, d in nodes.items() if d['v'] == v])
                       for v in {d['v'] for d in nodes.values() if d['v']}) if len(ids) > 1},
        'html_residue': [i for i, d in nodes.items() if '<' in (d['v'] or '')],
    }


# ---------- 報告 ----------

def report(path, nodes, edges, labels, orphans, ann, steps, attrib, chk):
    sid = lambda i: (i or 'None').split('-')[-1]
    shape = lambda d: ('◇判斷' if 'rhombus' in d['style']
                       else '○起迄' if ('ellipse' in d['style'] or 'terminator' in d['style'])
                       else '⬢容器' if 'swimlane' in d['style'] else '□步驟')
    nm = lambda i: f"{nodes.get(i, {}).get('v', '⛔懸空')[:36]}#{sid(i)}"
    L = []
    w = L.append
    w(f"檔案: {path}")
    w(f"節點 {len(nodes)}（步驟/判斷 {len(steps)} + 註解 {len(ann)}）｜ 連線 {len(edges)}（有標籤 {len(labels)}）")
    w(f"帶自訂屬性的節點: {sum(1 for d in nodes.values() if d['attrs'])}")

    w("\n===== 節點（上→下、左→右）=====")
    for i, d in sorted(nodes.items(), key=lambda kv: (kv[1]['y'], kv[1]['x'])):
        if not d['v']:
            continue
        w(f"{shape(d)} #{sid(i):>5} ({int(d['x'])},{int(d['y'])})  {d['v'][:70]}")

    w("\n===== 連線 =====")
    for i, e in sorted(edges.items(),
                       key=lambda kv: (nodes.get(kv[1]['source'], {}).get('y', 0),
                                       nodes.get(kv[1]['source'], {}).get('x', 0))):
        w(f"{nm(e['source'])}  --[{labels.get(i, '') or '無標籤'}]-->  {nm(e['target'])}")

    w("\n===== 結構檢查 =====")
    w(f"懸空連線(缺來源或目標): {len(chk['dangling'])}")
    w(f"脫鉤標籤(edgeLabel 但 parent=1): {len(orphans)}")
    for i, d in orphans.items():
        w(f"   ⛔ #{sid(i)} 「{d['v']}」 ({int(d['x'])},{int(d['y'])})")
    w(f"孤島節點: {len(chk['isolated'])}")
    for i in chk['isolated']:
        w(f"   ⛔ {nodes[i]['v'][:50]}#{sid(i)}")
    w(f"弱連通分量: {len(chk['components'])} 塊" + ("  ← 圖是斷的" if len(chk['components']) > 1 else ""))
    for k, c in enumerate(chk['components'], 1):
        if len(chk['components']) > 1:
            w(f"   第{k}塊({len(c)}): {', '.join(nodes[x]['v'][:16] + '#' + sid(x) for x in c)}")
    w(f"\n起點(只出不進): {[nodes[i]['v'][:30] for i in chk['sources']]}")
    w(f"終點(只進不出): {[nodes[i]['v'][:30] for i in chk['sinks']]}")
    if chk['dup_names']:
        w(f"\n同名節點 {len(chk['dup_names'])} 組（轉程式會撞名）:")
        for v, ids in chk['dup_names'].items():
            w(f"   「{v[:30]}」 × {len(ids)}: {[sid(i) for i in ids]}")
    if chk['html_residue']:
        w(f"\n殘留 HTML 標記的節點: {[sid(i) for i in chk['html_residue']]}")

    w("\n===== 判斷節點出口 =====")
    for i, d in nodes.items():
        if 'rhombus' not in d['style']:
            continue
        outs = [k for k, e in edges.items() if e['source'] == i]
        tags = [labels.get(k) or '(無標籤)' for k in outs]
        flag = '  ⚠️ 出口<2' if len(outs) < 2 else ('  ⚠️ 有出口缺標籤' if '(無標籤)' in tags else '')
        w(f"   ◇{d['v'][:34]}#{sid(i)} → {len(outs)} 出口: {tags}{flag}")

    if ann:
        w("\n===== 註解歸屬（幾何中心 + 歐氏距離）=====")
        by_step = defaultdict(list)
        for i, a in attrib.items():
            by_step[a['step']].append((i, a))
        for s, items in sorted(by_step.items(), key=lambda kv: (nodes[kv[0]]['y'], nodes[kv[0]]['x'])):
            w(f"\n▸ {nodes[s]['v'][:44]}#{sid(s)}")
            for i, a in sorted(items, key=lambda kv: nodes[kv[0]]['y']):
                margin = a['runner_up_dist'] - a['dist']
                warn = '  ⚠️ 與次近候選差距<40，歸屬可能不穩' if margin < 40 else ''
                w(f"    #{sid(i)} {nodes[i]['v'][:92]}{warn}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--out', default='drawio_report.txt')
    ap.add_argument('--json')
    a = ap.parse_args()

    root = load_xml(a.path)
    nodes, edges, labels, orphans = parse(root)
    ann, steps, attrib = attribute_annotations(nodes)
    chk = validate(nodes, edges, orphans, steps)
    text = report(a.path, nodes, edges, labels, orphans, ann, steps, attrib, chk)

    open(a.out, 'w', encoding='utf-8').write(text + "\n")
    if a.json:
        sid = lambda i: (i or 'None').split('-')[-1]
        json.dump({
            'nodes': [{'id': i, 'sid': sid(i), 'label': d['v'], 'shape': d['style'],
                       'x': d['x'], 'y': d['y'], 'attrs': d['attrs']} for i, d in nodes.items()],
            'edges': [{'source': e['source'], 'target': e['target'], 'label': labels.get(i, '')}
                      for i, e in edges.items()],
            'annotations': {i: attrib[i]['step'] for i in attrib},
            'problems': {k: v for k, v in chk.items() if k in
                         ('dangling', 'orphan_labels', 'isolated', 'sources', 'sinks', 'dup_names')},
        }, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    # 這行刻意用純 ASCII：Windows 主控台是 cp950，印中文會變亂碼（這支腳本要示範的正是這點）
    print(f"OK -> {a.out}   (read it with `cat`, do NOT rely on stdout)")


if __name__ == '__main__':
    main()
