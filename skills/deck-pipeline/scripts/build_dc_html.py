"""deck-pipeline: SLIDES.md + STYLE.md -> Claude Design 用的 deck-stage .dc.html

用法:
  py -3.12-64 build_dc_html.py <deck資料夾>            # 產 output/<title>.dc.html 與 output/<title>.upload.json

輸出的 .dc.html 跟桌面版 Claude Design 匯入 pptx 後自己生的格式一致 (x-import deck-stage, 一頁一個 section),
寫進 Claude Design 專案後可在 app 內美化並匯出 pptx。upload.json 列出 html 之外還要寫進專案的檔案 (SVG 與圖片) 及其相對路徑。

座標: STYLE.md 的英吋 box × 144 = 1920x1080 舞台上的 px; 字級 pt × 2 = px。
圖片由腳本算好等比 fit 尺寸直接寫死 (瀏覽器不會自己把 SVG 放大到 box)。
table 版型的表格與其後的 body 放同一個 flow 容器, 表格列數多長高時小結跟著往下, 不會疊到。
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pptx import (  # noqa: E402
    SVG_SUFFIX,
    TODO,
    Deck,
    Page,
    SlidesParseError,
    Style,
    StyleParseError,
    _svg_size_px,
    parse_slides,
    parse_style,
    safe_filename,
    validate,
)

PX_PER_INCH = 144  # 13.333in -> 1920px
PX_PER_PT = 2
STAGE_W, STAGE_H = 1920, 1080


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _px(v: float) -> int:
    return round(v * PX_PER_INCH)


def _box_style(box) -> str:
    x, y, w, h = (_px(v) for v in box)
    return f"position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;"


def _text_style(el: dict, theme: dict, *, font: str) -> str:
    size = el.get("size", 18) * PX_PER_PT
    color = el.get("color", theme["fg"])
    weight = 700 if el.get("bold") else 400
    return f"font-family:'{font}',sans-serif;font-size:{size}px;font-weight:{weight};color:{color};line-height:1.35;"


def _lines_inner(lines: list[str], el: dict, theme: dict, *, font: str, first_bold: bool = False, first_color: str | None = None) -> str:
    out = []
    for i, line in enumerate(lines):
        extra = ""
        if first_bold and i == 0:
            extra += "font-weight:700;"
        if first_color and i == 0:
            extra += f"color:{first_color};"
        out.append(f'<div style="{extra}">{_esc(line)}</div>')
    gap = round(el.get("size", 18) * PX_PER_PT * 0.55)
    return (
        f'<div style="{_text_style(el, theme, font=font)}'
        f'display:flex;flex-direction:column;gap:{gap}px;box-sizing:border-box;">{"".join(out)}</div>'
    )


def _bullets_inner(lines: list[str], el: dict, theme: dict) -> str:
    size = el.get("size", 18) * PX_PER_PT
    dot = max(8, round(size * 0.3))
    items = []
    for line in lines:
        items.append(
            f'<div style="display:flex;gap:{round(size * 0.5)}px;align-items:baseline;">'
            f'<div style="width:{dot}px;height:{dot}px;border-radius:50%;background:{theme["accent"]};flex:none;transform:translateY(-{round(size * 0.12)}px);"></div>'
            f'<div>{_esc(line)}</div></div>'
        )
    gap = round(size * 0.6)
    return (
        f'<div style="{_text_style(el, theme, font=theme["font_body"])}'
        f'display:flex;flex-direction:column;gap:{gap}px;box-sizing:border-box;">{"".join(items)}</div>'
    )


def _positioned(inner: str, box) -> str:
    """把 flow 元素的外層 div 加上絕對定位 box"""
    return inner.replace('<div style="', f'<div style="{_box_style(box)}', 1)


def _image_size_px(path: Path) -> tuple[float, float]:
    if path.suffix.lower() == SVG_SUFFIX:
        return _svg_size_px(ET.parse(str(path)).getroot())
    with Image.open(path) as im:
        return im.size


def _image_block(desc: str, path: str, el: dict, theme: dict, deck_dir: Path) -> str:
    x, y, w, h = (v * PX_PER_INCH for v in el["box"])
    if path == TODO:
        return (
            f'<div style="{_box_style(el["box"])}background:#D1D5DB;display:flex;align-items:center;justify-content:center;'
            f'font-family:\'{theme["font_body"]}\',sans-serif;font-size:28px;color:{theme["fg"]};text-align:center;padding:24px;box-sizing:border-box;">'
            f'[待補圖] {_esc(desc)}</div>'
        )
    iw, ih = _image_size_px(deck_dir / path)
    scale = min(w / iw, h / ih)
    pw, ph = round(iw * scale), round(ih * scale)
    px, py = round(x + (w - iw * scale) / 2), round(y + (h - ih * scale) / 2)
    src = quote(path, safe="/")
    return f'<img src="{src}" alt="{_esc(desc)}" style="position:absolute;left:{px}px;top:{py}px;width:{pw}px;height:{ph}px;"/>'


def _table_inner(rows: list[list[str]], el: dict, theme: dict) -> str:
    if not rows:
        return ""
    size = el.get("size", 18) * PX_PER_PT
    header_bg = el.get("header_bg", theme.get("accent", theme["fg"]))
    header_fg = el.get("header_fg", theme["bg"])
    fg = el.get("color", theme["fg"])
    pad = f"{round(size * 0.2)}px {round(size * 0.4)}px"  # 對齊 pptx 儲存格預設邊距的比例
    ncols = max(len(r) for r in rows)
    trs = []
    for r, row in enumerate(rows):
        tds = []
        for c in range(ncols):
            cell = row[c] if c < len(row) else ""
            if r == 0:
                tds.append(
                    f'<th style="background:{header_bg};color:{header_fg};font-weight:700;text-align:left;'
                    f'padding:{pad};border:1px solid {header_bg};">{_esc(cell)}</th>'
                )
            else:
                tds.append(
                    f'<td style="background:{theme["bg"]};color:{fg};padding:{pad};border:1px solid #D9D0C4;">{_esc(cell)}</td>'
                )
        trs.append(f"<tr>{''.join(tds)}</tr>")
    return (
        f'<table style="width:100%;border-collapse:collapse;font-family:\'{theme["font_body"]}\',sans-serif;'
        f'font-size:{size}px;line-height:1.2;">{"".join(trs)}</table>'
    )


def _column(page: Page, idx: int) -> list[str]:
    return [row[idx] for row in page.table if len(row) > idx]


def _body_lines(page: Page, has_subtitle_el: bool) -> list[str]:
    return page.bullets or ([] if has_subtitle_el else page.subtitle.splitlines())


def _body_inner(page: Page, el: dict, theme: dict, has_subtitle_el: bool) -> str:
    lines = _body_lines(page, has_subtitle_el)
    if not lines:
        return ""
    if page.bullets:
        return _bullets_inner(lines, el, theme)
    return _lines_inner(lines, el, theme, font=theme["font_body"])


def render_page(page: Page, num: int, style: Style, deck_dir: Path) -> str:
    theme = style.theme
    elements = list(style.layouts[page.layout])
    has_subtitle_el = any(el["role"] == "subtitle" for el in elements)
    parts = []
    img_i = 0
    i = 0
    while i < len(elements):
        el = elements[i]
        role = el["role"]
        if role == "title":
            parts.append(_positioned(_lines_inner([page.title], el, theme, font=theme["font_title"]), el["box"]))
        elif role == "subtitle":
            if page.subtitle:
                parts.append(_positioned(_lines_inner(page.subtitle.splitlines(), el, theme, font=theme["font_body"]), el["box"]))
        elif role == "body":
            inner = _body_inner(page, el, theme, has_subtitle_el)
            if inner:
                parts.append(_positioned(inner, el["box"]))
        elif role == "image":
            if img_i < len(page.images):
                desc, path = page.images[img_i]
                img_i += 1
                parts.append(_image_block(desc, path, el, theme, deck_dir))
        elif role in ("left", "right"):
            col = 0 if role == "left" else 1
            inner = _lines_inner(_column(page, col), el, theme, font=theme["font_body"], first_bold=True,
                                 first_color=theme["accent"] if role == "left" else None)
            parts.append(_positioned(inner, el["box"]))
        elif role == "table":
            table_html = _table_inner(page.table, el, theme)
            nxt = elements[i + 1] if i + 1 < len(elements) else None
            if nxt and nxt["role"] == "body":
                tx, ty, tw, th = el["box"]
                bx, by, bw, bh = nxt["box"]
                gap = max(_px(by - ty - th), 24)
                total_h = _px(by + bh - ty)
                body_html = _body_inner(page, nxt, theme, has_subtitle_el)
                parts.append(
                    f'<div style="position:absolute;left:{_px(tx)}px;top:{_px(ty)}px;width:{_px(tw)}px;height:{total_h}px;'
                    f'display:flex;flex-direction:column;gap:{gap}px;">{table_html}{body_html}</div>'
                )
                i += 1
            else:
                parts.append(f'<div style="{_box_style(el["box"])}">{table_html}</div>')
        else:
            raise StyleParseError(f"版型 {page.layout} 有未知 role: {role}")
        i += 1
    notes = _esc(page.notes.replace("\n", " ")) if page.notes else ""
    return (
        f'<section data-label="{_esc(page.title)}" data-screen-label="{num:02d}" data-speaker-notes="{notes}" '
        f'style="position:relative;width:{STAGE_W}px;height:{STAGE_H}px;background:{theme["bg"]};color:{theme["fg"]};'
        f'font-family:\'{theme["font_body"]}\',sans-serif;overflow:hidden;box-sizing:border-box;">\n'
        + "\n".join(parts)
        + "\n</section>"
    )


def render(deck: Deck, style: Style, deck_dir: Path) -> str:
    theme = style.theme
    fonts = {theme["font_title"], theme["font_body"]}
    font_q = "&amp;".join("family=" + quote(f).replace("%20", "+") + ":wght@400;700" for f in sorted(fonts))
    sections = []
    for n, (_topic, _i, page) in enumerate(deck.pages(), 1):
        sections.append(render_page(page, n, style, deck_dir))
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{font_q}&amp;display=swap">
<style>
body{{margin:0;background:#EFEAE3;}}
a{{color:{theme["accent"]};text-decoration:none}}a:hover{{color:{theme["fg"]}}}
</style>
</helmet>
<x-import component-from-global-scope="deck-stage" from="./deck-stage.js" width="{STAGE_W}" height="{STAGE_H}" hint-size="100%,100%">

{chr(10).join(sections)}

</x-import>
</x-dc>
</body>
</html>
"""


def upload_manifest(deck: Deck, deck_dir: Path) -> dict:
    """html 之外要寫進 Claude Design 專案的檔案: 每個非 TODO 圖片一筆, 相對路徑即專案內路徑"""
    text_files, binary_files = [], []
    seen = set()
    for _topic, _i, page in deck.pages():
        for _desc, path in page.images:
            if path == TODO or path in seen:
                continue
            seen.add(path)
            (text_files if path.lower().endswith(SVG_SUFFIX) else binary_files).append(
                {"path": path, "bytes": (deck_dir / path).stat().st_size}
            )
    return {"text": text_files, "binary": binary_files}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck_dir", help="工作資料夾, 內含 SLIDES.md 與 STYLE.md")
    args = ap.parse_args(argv)
    try:
        deck_dir = Path(args.deck_dir).resolve()
        deck = parse_slides((deck_dir / "SLIDES.md").read_text(encoding="utf-8"))
        style = parse_style((deck_dir / "STYLE.md").read_text(encoding="utf-8"))
        errors = validate(deck, style, deck_dir)
        if errors:
            print("build 失敗:")
            for e in errors:
                print(" -", e)
            return 1
        out_dir = deck_dir / "output"
        out_dir.mkdir(exist_ok=True)
        name = safe_filename(deck.title)
        out = out_dir / f"{name}.dc.html"
        out.write_text(render(deck, style, deck_dir), encoding="utf-8")
        manifest = out_dir / f"{name}.upload.json"
        manifest.write_text(json.dumps(upload_manifest(deck, deck_dir), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已輸出 {out}")
        print(f"已輸出 {manifest}")
        return 0
    except (SlidesParseError, StyleParseError, FileNotFoundError, PermissionError, KeyError) as e:
        print(f"build 失敗: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
