#!/usr/bin/env python3
"""
GDD vault 稽核腳本。

掃描一個 Obsidian vault（或任何裝滿 .md 的資料夾），回報機械可驗證的完成度問題：
斷掉的 wikilink、孤兒檔、空檔、佔位符、以及索引檔裡沒有連結的項目。

這些是「不用讀內文就能確定有問題」的部分。真正需要判斷的東西
（章節斷在一半、缺數值表、跨文件矛盾、名詞不統一）還是得實際讀檔。

用法:
    python3 audit_vault.py <vault路徑> [--index README.md]
"""

import argparse
import os
import re
import sys
from collections import defaultdict

# 內文中代表「這裡還沒定案」的訊號
PLACEHOLDER_PATTERNS = [
    (r"待定", "待定"),
    (r"暫定", "暫定"),
    (r"待補", "待補"),
    (r"待確認", "待確認"),
    (r"待平衡", "待平衡"),
    (r"另述|另行定義|後續補充", "外包給不存在的文件"),
    (r"\bTBD\b", "TBD"),
    (r"\bTODO\b", "TODO"),
    (r"\?\?", "??"),
]
# 注意：刻意不把 {數值} / {數字} 列為佔位符。在這個 vault 裡它是
# 「顯示格式」的正規寫法（例如 `${數值}/每日`），不是未定案標記，
# 全部抓出來只會淹沒真正需要處理的項目。

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")

# 擷取 [[連結]]，同時容許 [[連結|別名]] 與 [[連結#區塊]]
WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)")


def stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def collect(vault):
    """回傳 (檔名stem -> 相對路徑, 檔名stem -> 內文)"""
    files, texts = {}, {}
    for root, dirs, names in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for n in names:
            if not n.endswith(".md"):
                continue
            full = os.path.join(root, n)
            key = stem(n)
            files[key] = os.path.relpath(full, vault)
            try:
                with open(full, encoding="utf-8") as f:
                    texts[key] = f.read()
            except UnicodeDecodeError:
                texts[key] = ""
                print(f"  ! 無法以 UTF-8 讀取：{files[key]}", file=sys.stderr)
    return files, texts


def build_links(texts):
    """回傳 目標 -> {來源檔案}，已排除圖片連結"""
    links = defaultdict(set)
    for src, body in texts.items():
        for target in WIKILINK_RE.findall(body):
            target = target.strip()
            if target.lower().endswith(IMAGE_EXT):
                continue
            links[target].add(src)
    return links


def find_placeholders(texts):
    """回傳 檔名 -> [(行號, 標籤, 該行內容)]"""
    hits = defaultdict(list)
    for name, body in texts.items():
        for i, line in enumerate(body.splitlines(), 1):
            for pattern, label in PLACEHOLDER_PATTERNS:
                if re.search(pattern, line):
                    snippet = line.strip()
                    if len(snippet) > 90:
                        snippet = snippet[:90] + "…"
                    hits[name].append((i, label, snippet))
                    break
    return hits


def index_orphans(texts, files, index_name):
    """索引檔裡以純文字列出、但既沒有 wikilink 也沒有對應檔案的項目。

    抓的是 markdown 清單項目中不含 [[ ]] 的文字，這通常代表
    『規劃了但還沒開檔』的系統。
    """
    body = texts.get(index_name)
    if body is None:
        return None

    lines = body.splitlines()
    entries = []  # (縮排深度, 項目文字)
    for line in lines:
        m = re.match(r"^(\s*)[-*+]\s+(.+?)\s*$", line)
        entries.append((len(m.group(1)), m.group(2)) if m else None)

    missing = []
    for i, e in enumerate(entries):
        if e is None:
            continue
        indent, item = e
        # 父節點（下一個清單項目縮排更深）是分類標題，不是待建檔的系統
        nxt = next((x for x in entries[i + 1:] if x is not None), None)
        if nxt and nxt[0] > indent:
            continue
        if "[[" in item or item.startswith("**"):
            continue
        item = re.sub(r"[`*]", "", item).strip()
        # 過濾掉明顯是敘述句而非系統名稱的行
        if not item or len(item) > 20 or "：" in item or "。" in item:
            continue
        if item not in files:
            missing.append(item)
    return missing


def main():
    ap = argparse.ArgumentParser(description="盤點 GDD vault 的完成度")
    ap.add_argument("vault", help="vault 根目錄")
    ap.add_argument("--index", default="README", help="索引檔名（不含副檔名），預設 README")
    args = ap.parse_args()

    if not os.path.isdir(args.vault):
        sys.exit(f"找不到目錄：{args.vault}")

    files, texts = collect(args.vault)
    if not files:
        sys.exit("這個目錄裡沒有 .md 檔")

    links = build_links(texts)

    print(f"# Vault 稽核報告：{os.path.abspath(args.vault)}")
    print(f"\n共 {len(files)} 份 .md 檔。\n")

    # 1. 空檔
    empty = sorted(n for n, b in texts.items() if not b.strip())
    print("## 1. 空檔（0 bytes 或只有空白）\n")
    if empty:
        for n in empty:
            refs = sorted(links.get(n, []))
            ref_txt = f"　← 被 {', '.join(refs)} 連結" if refs else "　（無人連結）"
            print(f"- `{files[n]}`{ref_txt}")
    else:
        print("（無）")

    # 2. 斷鏈
    print("\n## 2. 斷鏈：被連結但檔案不存在\n")
    broken = sorted(t for t in links if t not in files)
    if broken:
        for t in broken:
            print(f"- `{t}`　← 被 {', '.join(sorted(links[t]))} 連結")
    else:
        print("（無）")

    # 3. 孤兒檔
    print("\n## 3. 孤兒檔：存在但沒有任何檔案連結它\n")
    orphans = sorted(n for n in files if n not in links and n != args.index)
    if orphans:
        for n in orphans:
            print(f"- `{files[n]}`")
    else:
        print("（無）")

    # 4. 索引裡有名字但沒開檔
    missing = index_orphans(texts, files, args.index)
    print(f"\n## 4. 索引（{args.index}.md）列出但尚未建檔\n")
    if missing is None:
        print(f"（找不到索引檔 {args.index}.md，略過）")
    elif missing:
        for item in missing:
            print(f"- {item}")
    else:
        print("（無）")

    # 5. 佔位符
    print("\n## 5. 佔位符與未定案標記\n")
    hits = find_placeholders(texts)
    if hits:
        for name in sorted(hits, key=lambda n: -len(hits[n])):
            print(f"\n### `{files[name]}`（{len(hits[name])} 處）\n")
            for line_no, label, snippet in hits[name][:12]:
                print(f"- L{line_no} [{label}] {snippet}")
            if len(hits[name]) > 12:
                print(f"- …另有 {len(hits[name]) - 12} 處")
    else:
        print("（無）")

    print("\n---\n")
    print("以上為機械可驗證的部分。以下仍需實際讀檔判斷，腳本抓不到：\n")
    print("- 章節寫到一半就斷句、標題承諾了但內文沒寫")
    print("- 只有質化描述、缺數值表或公式")
    print("- 跨文件的規則互相矛盾")
    print("- 同一個東西有多個名字，或同一個名字指多個東西")


if __name__ == "__main__":
    main()
