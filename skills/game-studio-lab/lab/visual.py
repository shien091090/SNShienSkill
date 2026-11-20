"""視覺設計階段的純函式: 元素清單 / 挑選結果解析、方案頁、視覺方向。設計見 docs/2026-11-19-visual-design-stage-design.md。"""
import html
import json
import re
from pathlib import Path

OPTION_IDS = ("A", "B", "C")
CODE_RE = re.compile(r"^[a-z][a-z0-9-]*$")
KINDS = {"靜態": "static", "動態": "anim"}
_KV = re.compile(r"^\s*[-*]?\s*([^:：]+?)\s*[:：]\s*(.*?)\s*$")


def parse_elements(text: str) -> dict:
    """elements.md → {"base", "elements": [{code, name, kind, content, why}]}; 格式不對丟 ValueError。"""
    base, sections, cur = "", [], None
    for line in text.splitlines():
        h = re.match(r"^##\s+(\S+)\s*[—–-]+\s*(.+?)\s*$", line)
        if h:
            cur = {"code": h.group(1), "name": h.group(2), "fields": {}}
            sections.append(cur)
            continue
        m = _KV.match(line)
        if not m or not m.group(2):
            continue
        if cur is None:
            if m.group(1) == "底版":
                base = m.group(2).strip("`")
        else:
            cur["fields"][m.group(1)] = m.group(2)
    if not base:
        raise ValueError("元素清單開頭缺「底版: <深掘資料夾>/<款>」")
    if not sections:
        raise ValueError("元素清單沒有任何元素(每個元素一節「## 代號 — 名稱」)")
    out = []
    for s in sections:
        if not CODE_RE.match(s["code"]):
            raise ValueError(f"元素代號「{s['code']}」只能用英文小寫、數字與連字號")
        f = s["fields"]
        missing = [k for k in ("類型", "內容") if not f.get(k)]
        if missing:
            raise ValueError(f"元素 {s['code']} 缺: {'、'.join(missing)}")
        if f["類型"] not in KINDS:
            raise ValueError(f"元素 {s['code']} 的類型「{f['類型']}」只能是 靜態 或 動態")
        out.append({"code": s["code"], "name": s["name"], "kind": KINDS[f["類型"]],
                    "content": f["內容"], "why": f.get("為什麼是核心", "")})
    return {"base": base, "elements": out}


def parse_visual_pick(text: str, codes: list[str], redo: bool = False) -> dict:
    """pick.md → {code: {"id", "note"}}。pick 每個元素都要有 A/B/C; redo 只列要重做的, 方案代號可省。"""
    out = {}
    for line in text.splitlines():
        m = _KV.match(line)
        if not m or not m.group(2):
            continue
        code, rest = m.group(1), m.group(2)
        if code not in codes:
            raise ValueError(f"沒有元素「{code}」, 可用: {', '.join(codes)}")
        parts = re.split(r"[,，]", rest, maxsplit=1)
        head, note = parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")
        if head.upper() in OPTION_IDS:
            out[code] = {"id": head.upper(), "note": note}
        elif redo:
            out[code] = {"id": "", "note": rest.strip()}
        else:
            raise ValueError(f"元素 {code} 的方案「{head}」只能是 {'/'.join(OPTION_IDS)}")
    if redo:
        if not out:
            raise ValueError("重做要列出至少一個元素, 例「hero: 都太細, 要更粗獷」")
        return out
    missing = [c for c in codes if c not in out]
    if missing:
        raise ValueError(f"挑選結果漏了: {', '.join(missing)}")
    return out


def missing_options(options_dir: Path, codes: list[str]) -> list[str]:
    names = [n for c in codes for n in [*(f"{c}-{i}.js" for i in OPTION_IDS), f"{c}.md"]]
    return [n for n in names if not (Path(options_dir) / n).exists()]


def option_notes(options_dir: Path, code: str) -> dict:
    """<code>.md 的「A: 說明」→ {"A": "說明"}。"""
    p = Path(options_dir) / f"{code}.md"
    notes = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            m = _KV.match(line)
            if m and m.group(1).upper() in OPTION_IDS:
                notes[m.group(1).upper()] = m.group(2)
    return notes


_CSS = """
body{margin:0;padding:24px 16px;background:#f6f4f8;color:#2d2144;font-family:"Noto Sans TC","Microsoft JhengHei",sans-serif}
main{max-width:1400px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px}h2{font-size:18px;margin:36px 0 4px}
.why{font-size:13px;opacity:.8;margin:0 0 12px}
.row{display:grid;grid-template-columns:1fr;gap:20px}
.opt{background:#fff;border-radius:12px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:0}
.opt h3{margin:0 0 8px;font-size:16px}
canvas{display:block;width:100%;height:auto;background:#222;border-radius:6px}
.ctl{display:flex;align-items:center;gap:8px;margin-top:8px}
.ctl button{font:inherit;font-size:14px;padding:4px 14px;border-radius:999px;border:1px solid #2d2144;background:#fff;color:#2d2144;cursor:pointer}
.ctl input{flex:1}
.note{font-size:13px;margin-top:8px}
.note summary{cursor:pointer;opacity:.6}
"""

_JS = """
function setup(opt, box){
  var c = document.createElement('canvas'), x = c.getContext('2d');
  c.width = opt.size[0]; c.height = opt.size[1]; box.appendChild(c);
  function frame(t){
    x.save(); x.setTransform(1,0,0,1,0,0); x.clearRect(0,0,c.width,c.height);
    try { opt.draw(x, t); } catch(e) {
      x.setTransform(1,0,0,1,0,0); x.fillStyle='#fff'; x.font='16px sans-serif'; x.fillText('方案程式出錯: '+e.message, 12, 28);
    }
    x.restore();
  }
  if (opt.kind !== 'anim') { frame(0); return; }
  var dur = opt.duration || 3, t = 0, playing = false, last = 0;
  var ctl = document.createElement('div'); ctl.className = 'ctl';
  var btn = document.createElement('button'); btn.textContent = '播放';
  var bar = document.createElement('input'); bar.type = 'range'; bar.min = 0; bar.max = dur; bar.step = 0.01; bar.value = 0;
  ctl.appendChild(btn); ctl.appendChild(bar); box.appendChild(ctl);
  function tick(now){
    if (!playing) return;
    t += (now - last) / 1000; last = now;
    if (t >= dur) { if (opt.loop) t = t % dur; else { t = dur; playing = false; btn.textContent = '播放'; } }
    bar.value = t; frame(t);
    if (playing) requestAnimationFrame(tick);
  }
  btn.onclick = function(){
    playing = !playing; btn.textContent = playing ? '暫停' : '播放';
    if (playing) { if (t >= dur) t = 0; last = performance.now(); requestAnimationFrame(tick); }
  };
  bar.oninput = function(){ t = +bar.value; frame(t); };
  frame(0);
}
document.querySelectorAll('[data-opt]').forEach(function(box){
  var opt = window.__OPTS[+box.dataset.opt];
  if (opt) setup(opt, box); else box.insertAdjacentHTML('afterbegin', '<p>方案程式沒有定義 VISUAL_OPTION</p>');
});
"""


def build_visual_page(visual_dir: Path, elements: list[dict], art_js: Path) -> Path:
    """單一 HTML: 內嵌底版 art.js 與所有方案程式(Artifact 是單頁, 不能靠相對路徑)。"""
    e = html.escape
    opts_dir = Path(visual_dir) / "options"
    scripts, sections, n = [], [], 0
    for el in elements:
        notes = option_notes(opts_dir, el["code"])
        cells = []
        for i in OPTION_IDS:
            src = (opts_dir / f"{el['code']}-{i}.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
            scripts.append(f"<script>window.VISUAL_OPTION=null;\n{src}\n;window.__OPTS.push(window.VISUAL_OPTION);</script>")
            cells.append(f'<div class="opt"><h3>{e(el["code"])} 方案 {i}</h3><div data-opt="{n}"></div>'
                         f'<details class="note"><summary>方案說明</summary>{e(notes.get(i, ""))}</details></div>')
            n += 1
        kind = "動態" if el["kind"] == "anim" else "靜態"
        # 使用者看圖挑方案: 元素內容與方案說明不攤開(說明收進可展開的小字), 每個方案獨佔一列、畫布用滿寬度
        sections.append(f'<h2>{e(el["name"])}（{e(el["code"])}，{kind}）</h2>'
                        f'<div class="row">{"".join(cells)}</div>')
    art = Path(art_js).read_text(encoding="utf-8").replace("</script", "<\\/script")
    page = (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>視覺方案</title>'
            f"<style>{_CSS}</style></head><body><main><h1>視覺方案</h1>"
            f'<p class="why">動態方案按「播放」。回覆例「title: B」。</p>'
            f'{"".join(sections)}</main><script>window.__OPTS=[];</script><script>{art}</script>'
            f'{"".join(scripts)}<script>{_JS}</script></body></html>')
    out = opts_dir / "index.html"
    out.write_text(page, encoding="utf-8")
    return out


def write_direction(visual_dir: Path, parsed: dict, picks: dict) -> Path:
    """定案的視覺方向: 打磨的設計與美術照這份做。"""
    opts_dir = Path(visual_dir) / "options"
    lines = ["# 視覺方向", "", f"底版: {parsed['base']}", "",
             "打磨照這份做: 規格的對應段落照方向寫; 美術把選中的方案程式當起點, 搬進 art.js 改成遊戲用的函式。", ""]
    for el in parsed["elements"]:
        p = picks[el["code"]]
        note = option_notes(opts_dir, el["code"]).get(p["id"], "")
        lines += [f"## {el['code']} — {el['name']}", f"- 選中: 方案 {p['id']}({note})",
                  f"- 方案程式: options/{el['code']}-{p['id']}.js", f"- 內容: {el['content']}"]
        if p["note"]:
            lines.append(f"- 使用者附註: {p['note']}")
        lines.append("")
    out = Path(visual_dir) / "direction.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
