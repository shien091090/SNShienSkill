"""把 reconcile.py 的結果 JSON 轉成對帳報告 HTML (發布用的 Artifact 頁面)。

用法: python report.py --result <結果 JSON> --out <HTML 路徑>
"""
import argparse
import html
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

ap = argparse.ArgumentParser()
ap.add_argument("--result", required=True)
ap.add_argument("--out", required=True)
args = ap.parse_args()
try:
    d = json.load(open(args.result, encoding="utf-8"))
except (OSError, ValueError) as ex:
    print(f"錯誤: 讀不到比對結果 {args.result}: {ex}")
    sys.exit(1)
e = html.escape


def money(x):
    return f"${int(round(x)):,}"


def discount_label(rate):
    # 0.95 → 95折, 0.9 → 9折
    p = int(round(rate * 100))
    return f"{p // 10 if p % 10 == 0 else p}折"

def items_html(inv):
    rows = "".join(
        f'<tr><td>{e(i["name"])}</td><td class="num">{e(str(i["qty"]))}</td><td class="num">{money(i["amount"])}</td></tr>'
        for i in inv["items"])
    return f'<table class="items"><thead><tr><th>品名</th><th class="num">數量</th><th class="num">金額</th></tr></thead><tbody>{rows}</tbody></table>'

miss_rows = []
for k, inv in enumerate(d["missing"]):
    n = len(inv["items"])
    miss_rows.append(
        f'<tr class="row" tabindex="0" aria-expanded="false" data-k="{k}"><td class="date">{inv["date"][5:]}</td><td class="store">{e(inv["storeName"])}</td>'
        f'<td class="no">{e(inv["invoiceNo"])}</td><td class="num">{money(inv["netAmount"])}</td><td class="note">{n} 項品項 <span class="chev">▸</span></td></tr>'
        f'<tr class="detail" hidden id="d{k}"><td colspan="5">{items_html(inv)}</td></tr>')
if miss_rows:
    missing_block = f'''<div class="scroll"><table class="list miss"><thead><tr><th>日期</th><th>賣方名稱</th><th>發票號碼</th><th class="num">淨額</th><th>備註</th></tr></thead><tbody>{"".join(miss_rows)}</tbody></table></div>'''
else:
    missing_block = '<p class="allgood">🎉 所有發票皆已對到帳，無漏記！</p>'

match_rows = []
for inv in d["matched"]:
    disc = ""
    if inv.get("discount"):
        r = inv["discount"]
        disc = f' <span class="disc">（{discount_label(r["rate"])}後 {money(r["amount"])} 已入帳）</span>'
    match_rows.append(
        f'<tr><td class="date">{inv["date"][5:]}</td><td class="store">{e(inv["storeName"])}</td><td class="no">{e(inv["invoiceNo"])}</td>'
        f'<td class="num">{money(inv["netAmount"])}{disc}</td></tr>')

miss_total = sum(i["netAmount"] for i in d["missing"])

page = f'''<title>對帳報告 {d["start"][:7]}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: 單欄帳本, 頂部玉綠色帶 + 漏記表優先, 已比對收合在下 */
:root {{
  --bg: #F6F8F7; --surface: #FFFFFF; --fg: #1E2A25; --muted: #66756E; --line: #DDE5E1;
  --jade: #2B7A58; --on-jade: #FFFFFF;
  --ok-bg: #DCF0E5; --ok-fg: #1F6B47;
  --warn-bg: #FBE9DF; --warn-fg: #B4542A; --warn-line: #D9663A; --warn-head: #FBE9DF;
  --font-body: "Noto Sans TC", "Microsoft JhengHei", "PingFang TC", sans-serif;
  --font-mono: "IBM Plex Mono", Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #121815; --surface: #1A221E; --fg: #E3EBE7; --muted: #94A49C; --line: #2C3832;
  --jade: #1F5C42; --on-jade: #F2F7F4;
  --ok-bg: #1E3B2D; --ok-fg: #8FD4AF;
  --warn-bg: #3A2519; --warn-fg: #F0A47E; --warn-line: #E07A4D; --warn-head: #2E2019;
  color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #121815; --surface: #1A221E; --fg: #E3EBE7; --muted: #94A49C; --line: #2C3832;
  --jade: #1F5C42; --on-jade: #F2F7F4;
  --ok-bg: #1E3B2D; --ok-fg: #8FD4AF;
  --warn-bg: #3A2519; --warn-fg: #F0A47E; --warn-line: #E07A4D; --warn-head: #2E2019;
  color-scheme: dark; }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--font-body); line-height: 1.55; }}
.wrap {{ max-width: 960px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
header {{ background: var(--jade); color: var(--on-jade); }}
header .wrap {{ padding-block: 28px 24px; display: grid; gap: 6px; }}
.eyebrow {{ font-size: 12px; letter-spacing: .12em; opacity: .85; }}
h1 {{ margin: 0; font-size: 28px; font-weight: 700; text-wrap: balance; }}
.range {{ font-family: var(--font-mono); font-size: 14px; opacity: .9; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
.chip {{ padding: 4px 12px; border-radius: 999px; font-size: 13px; font-weight: 500; font-variant-numeric: tabular-nums; }}
.chip.total {{ background: rgba(255,255,255,.18); color: var(--on-jade); }}
.chip.ok {{ background: var(--ok-bg); color: var(--ok-fg); }}
.chip.warn {{ background: var(--warn-bg); color: var(--warn-fg); }}
main .wrap {{ padding-block: 24px 40px; display: grid; gap: 24px; }}
section.missing {{ background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--warn-line); border-radius: 6px; overflow: hidden; }}
.sechead {{ background: var(--warn-head); color: var(--warn-fg); padding: 12px 16px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; font-weight: 700; }}
.sechead span {{ font-weight: 500; font-size: 13px; font-variant-numeric: tabular-nums; }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
th, td {{ text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }}
th {{ font-size: 12px; color: var(--muted); font-weight: 500; letter-spacing: .04em; white-space: nowrap; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.date, .no {{ font-family: var(--font-mono); font-size: 13px; white-space: nowrap; }}
.store {{ min-width: 12em; }}
.note {{ color: var(--muted); font-size: 13px; white-space: nowrap; }}
tr.row {{ cursor: pointer; }}
tr.row:hover, tr.row:focus-visible {{ background: var(--warn-bg); outline: none; }}
tr.row[aria-expanded="true"] .chev {{ display: inline-block; transform: rotate(90deg); }}
tr.detail td {{ background: var(--bg); padding: 4px 12px 12px 28px; }}
table.items {{ font-size: 13px; }}
table.items td, table.items th {{ padding: 5px 8px; }}
.allgood {{ padding: 20px 16px; margin: 0; }}
details.matched {{ background: var(--surface); border: 1px solid var(--line); border-radius: 6px; }}
details.matched summary {{ padding: 12px 16px; cursor: pointer; color: var(--muted); font-weight: 500; }}
details.matched table {{ color: var(--muted); }}
.disc {{ color: var(--muted); font-size: 12px; }}
footer {{ color: var(--muted); font-size: 13px; max-width: 65ch; }}
@media (prefers-reduced-motion: no-preference) {{ .chev {{ transition: transform .15s; }} }}
</style>
<header><div class="wrap">
  <div class="eyebrow">SNShien · 發票對帳</div>
  <h1>對帳報告</h1>
  <div class="range">{d["start"]} – {d["end"]}</div>
  <div class="chips">
    <span class="chip total">發票總數 {d["invoiceCount"]}</span>
    <span class="chip ok">已比對 {len(d["matched"])}</span>
    <span class="chip warn">可能漏記 {len(d["missing"])}</span>
  </div>
</div></header>
<main><div class="wrap">
  <section class="missing">
    <div class="sechead">可能漏記 <span>{len(d["missing"])} 張 · 合計 {money(miss_total)} · 點列展開品項</span></div>
    {missing_block}
  </section>
  <details class="matched">
    <summary>已比對 {len(d["matched"])} 張</summary>
    <div class="scroll"><table class="list"><thead><tr><th>日期</th><th>賣方名稱</th><th>發票號碼</th><th class="num">淨額</th></tr></thead><tbody>{"".join(match_rows)}</tbody></table></div>
  </details>
  <footer>比對邏輯（兩段式 ± 1 日）：① 先找當日與前一日記帳中單筆金額精確相符者；② 其餘以 exact subset sum 找一組記帳加總相符者補配。折扣商家（如新知喬 95 折）會同時嘗試原金額與折扣後金額。金額無法對齊時標記為可能漏記，請人工確認。</footer>
</div></main>
<script>
document.querySelectorAll("tr.row").forEach(function (r) {{
  function toggle() {{
    var det = document.getElementById("d" + r.dataset.k);
    det.hidden = !det.hidden;
    r.setAttribute("aria-expanded", String(!det.hidden));
  }}
  r.addEventListener("click", toggle);
  r.addEventListener("keydown", function (ev) {{ if (ev.key === "Enter" || ev.key === " ") {{ ev.preventDefault(); toggle(); }} }});
}});
</script>
'''
open(args.out, "w", encoding="utf-8").write(page)
print(f"報告: {args.out}")
