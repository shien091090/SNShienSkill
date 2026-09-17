"""svgtrace — 把一張圖臨摹成 SVG, 再轉成 PowerPoint 原生可編輯圖案。

四個子命令:
    grab     從剪貼簿取圖存檔
    palette  取原圖主色與指定座標的顏色
    render   用 Chrome headless 把 SVG 截圖, 可與原圖並排比對
    build    驗證 SVG 並轉成簡報裡的原生圖案 (新建或追加一頁)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from lxml import etree
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.util import Inches

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))

from svg_to_pptx import ConvertContext, EMU_PER_PX, collect_defs, convert_element
from svg_to_pptx.drawingml_converter import _collect_unsupported_visuals
from svg_to_pptx.drawingml_utils import SVG_NS

MARGIN_IN = 0.5
DEFAULT_W_IN, DEFAULT_H_IN = 13.333, 7.5

CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)
GUTTER_PX = 16
LABEL_PX = 24

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


class SvgTraceError(Exception):
    """使用者看得懂的錯誤。main() 捕捉後印一行訊息並回傳 1, 不吐 traceback。"""


def _px(value: str, attr: str, filename: str) -> float:
    """去掉 px / pt / % 之類的單位尾巴, 只留數字"""
    stripped = re.sub(r"[a-z%]+$", "", value.strip())
    try:
        return float(stripped)
    except ValueError as e:
        raise SvgTraceError(f"{filename} 的 {attr} 值無效: {value}") from e


def svg_size_px(svg_path: Path) -> tuple[float, float]:
    """SVG 的像素寬高。優先讀 viewBox, 沒有才退回 width/height"""
    if not svg_path.exists():
        raise SvgTraceError(f"檔案不存在: {svg_path}")
    try:
        root = ET.parse(str(svg_path)).getroot()
    except ET.ParseError as e:
        raise SvgTraceError(f"SVG 解析失敗 {svg_path.name}: {e}") from e
    vb = root.get("viewBox")
    if vb:
        try:
            _, _, vw, vh = (float(v) for v in vb.replace(",", " ").split())
        except ValueError as e:
            raise SvgTraceError(f"{svg_path.name} 的 viewBox 格式不正確: {vb}") from e
        return vw, vh
    w, h = root.get("width"), root.get("height")
    if not w or not h:
        raise SvgTraceError(f"{svg_path.name} 沒有 viewBox 也沒有 width/height, 無法決定尺寸")
    return _px(w, "width", svg_path.name), _px(h, "height", svg_path.name)


def fit_box(vw_px: float, vh_px: float, box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """把 vw_px x vh_px 的圖等比縮放置中塞進 box。box 與回傳值都是 (x, y, w, h) 英吋"""
    bx, by, bw, bh = box
    scale = min(bw / (vw_px / 96), bh / (vh_px / 96))
    gw, gh = (vw_px / 96) * scale, (vh_px / 96) * scale
    return bx + (bw - gw) / 2, by + (bh - gh) / 2, gw, gh


def svg_problems(svg_path: Path) -> list[str]:
    """驗證 SVG 能不能轉。回空 list 代表沒問題"""
    if not svg_path.exists():
        return [f"檔案不存在: {svg_path}"]
    try:
        root = ET.parse(str(svg_path)).getroot()
    except ET.ParseError as e:
        return [f"SVG 解析失敗 {svg_path.name}: {e}"]
    unsupported = _collect_unsupported_visuals(root)
    if unsupported:
        msg = f"SVG 含不支援元素 {svg_path.name}: {'; '.join(unsupported[:8])}"
        if len(unsupported) > 8:
            msg += f"，還有 {len(unsupported) - 8} 個"
        return [msg]
    return []


def _blank_layout(prs):
    """挑一個沒有版面配置區的版型; 都沒有就用最後一個, 之後再把配置區拔掉"""
    for layout in prs.slide_layouts:
        if len(layout.placeholders) == 0:
            return layout
    return prs.slide_layouts[-1]


def _add_blank_slide(prs):
    """加一頁純空白的投影片。

    追加進使用者自己的簡報時, 版型不一定有空白可選, 所以配置區一律拔掉,
    確保產出的那頁除了圖案以外什麼都沒有。
    """
    slide = prs.slides.add_slide(_blank_layout(prs))
    for shape in list(slide.placeholders):
        shape._element.getparent().remove(shape._element)
    return slide


def svg_group(slide, box, svg_path: Path, name: str) -> None:
    """SVG 變成一個原生圖案群組, 等比縮放置中塞進 box。

    群組內每個框/線/文字在 PowerPoint 裡都可個別編輯。
    """
    root = ET.parse(str(svg_path)).getroot()
    vw, vh = svg_size_px(svg_path)
    gx, gy, gw, gh = fit_box(vw, vh, box)

    sp_tree = slide.shapes._spTree
    used = [int(m) for m in re.findall(r'<p:cNvPr id="(\d+)"', etree.tostring(sp_tree).decode())]
    ctx = ConvertContext(defs=collect_defs(root), id_counter=max(used, default=1) + 1)

    frags = []
    for child in root:
        if child.tag.replace(f"{{{SVG_NS}}}", "") == "defs":
            continue
        result = convert_element(child, ctx)
        if result:
            frags.append(result.xml)

    gid = ctx.next_id()
    grp = (
        f'<p:grpSp xmlns:a="{A_NS}" xmlns:r="{R_NS}" xmlns:p="{P_NS}">'
        f'<p:nvGrpSpPr><p:cNvPr id="{gid}" name="{name}"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        f'<p:grpSpPr><a:xfrm>'
        f'<a:off x="{int(Inches(gx))}" y="{int(Inches(gy))}"/>'
        f'<a:ext cx="{int(Inches(gw))}" cy="{int(Inches(gh))}"/>'
        f'<a:chOff x="0" y="0"/>'
        f'<a:chExt cx="{int(vw * EMU_PER_PX)}" cy="{int(vh * EMU_PER_PX)}"/>'
        f'</a:xfrm></p:grpSpPr>'
        f'{"".join(frags)}</p:grpSp>'
    )
    sp_tree.append(etree.fromstring(grp))


def build(svg_path: Path, out_path: Path, name: str | None = None) -> Path:
    """驗證 SVG 後寫進 pptx。檔案不存在就建 16:9 新檔, 存在就追加一頁並沿用原尺寸"""
    problems = svg_problems(svg_path)
    if problems:
        raise SvgTraceError("\n".join(problems))

    if out_path.exists():
        prs = Presentation(str(out_path))
    else:
        prs = Presentation()
        prs.slide_width = Inches(DEFAULT_W_IN)
        prs.slide_height = Inches(DEFAULT_H_IN)

    box = (
        MARGIN_IN,
        MARGIN_IN,
        prs.slide_width.inches - 2 * MARGIN_IN,
        prs.slide_height.inches - 2 * MARGIN_IN,
    )
    slide = _add_blank_slide(prs)
    svg_group(slide, box, svg_path, name or svg_path.stem)

    try:
        prs.save(str(out_path))
    except PermissionError as e:
        raise SvgTraceError(f"{out_path.name} 正在被 PowerPoint 開著, 請先關掉再重跑") from e
    return out_path


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(rgb)


def palette(img_path: Path, n: int = 12, at: list[str] = ()) -> dict:
    """取原圖的主色與指定座標的精確顏色。

    量化只回答「這張圖大致有哪些色」, 但「那條線是什麼藍」要靠 at 點名問。
    """
    if not img_path.exists():
        raise SvgTraceError(f"圖片不存在: {img_path}")
    im = Image.open(img_path).convert("RGB")

    quantized = im.quantize(colors=min(256, max(2, n)))
    pal = quantized.getpalette()
    total = im.width * im.height
    colors = [
        {"hex": _hex(pal[idx * 3: idx * 3 + 3]), "ratio": count / total}
        for count, idx in sorted(quantized.getcolors(), reverse=True)
    ]

    samples = []
    for point in at:
        try:
            x, y = (int(v) for v in point.split(","))
        except ValueError as e:
            raise SvgTraceError(f"座標格式要寫成 X,Y: {point}") from e
        if not (0 <= x < im.width and 0 <= y < im.height):
            raise SvgTraceError(f"座標 {point} 超出圖片範圍 {im.width}x{im.height}")
        samples.append({"at": (x, y), "hex": _hex(im.getpixel((x, y)))})

    return {"size": im.size, "colors": colors, "samples": samples}


def find_chrome() -> Path:
    """依序找 CHROME 環境變數、Chrome、Edge。Edge 同為 Chromium, 截圖參數完全一樣"""
    env = os.environ.get("CHROME")
    if env and Path(env).exists():
        return Path(env)
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return Path(candidate)
    tried = [env or "(環境變數 CHROME 未設)", *CHROME_CANDIDATES]
    raise SvgTraceError("找不到 Chrome 或 Edge。找過這些位置:\n  " + "\n  ".join(tried))


def chrome_available() -> bool:
    try:
        find_chrome()
        return True
    except SvgTraceError:
        return False


def render(svg_path: Path, out_path: Path | None = None) -> Path:
    """用 Chrome headless 把 SVG 截成 PNG, 視窗尺寸直接用 SVG 的像素尺寸"""
    out = out_path or svg_path.with_suffix(".render.png")
    vw, vh = svg_size_px(svg_path)
    proc = subprocess.run(
        [
            str(find_chrome()),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--screenshot={out}",
            f"--window-size={int(round(vw))},{int(round(vh))}",
            "--default-background-color=FFFFFFFF",
            str(svg_path.resolve()),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if not out.exists():
        raise SvgTraceError(f"瀏覽器沒有產出截圖。訊息: {proc.stderr.strip()[:200]}")
    return out


def compare(original: Path, trace_png: Path, out_path: Path) -> Path:
    """原圖與臨摹圖等高並排, 中間留灰色分隔線。

    標籤刻意用英文, 避免踩到 Pillow 預設字型沒有中文字的問題。
    """
    left = Image.open(original).convert("RGB")
    right = Image.open(trace_png).convert("RGB")
    height = max(left.height, right.height)
    left = left.resize((round(left.width * height / left.height), height))
    right = right.resize((round(right.width * height / right.height), height))

    canvas = Image.new("RGB", (left.width + GUTTER_PX + right.width, height + LABEL_PX), "#FFFFFF")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([left.width, 0, left.width + GUTTER_PX, height + LABEL_PX], fill="#CCCCCC")
    draw.text((4, 6), "ORIGINAL", fill="#000000")
    draw.text((left.width + GUTTER_PX + 4, 6), "TRACE", fill="#000000")
    canvas.paste(left, (0, LABEL_PX))
    canvas.paste(right, (left.width + GUTTER_PX, LABEL_PX))
    canvas.save(out_path)
    return out_path


def _dispatch(args: argparse.Namespace) -> int:
    if args.cmd == "palette":
        result = palette(Path(args.image), args.n, args.at)
        print(f"尺寸 {result['size'][0]}x{result['size'][1]}")
        for c in result["colors"]:
            print(f"  {c['hex']}  {c['ratio'] * 100:5.1f}%")
        for s in result["samples"]:
            print(f"  取樣 {s['at'][0]},{s['at'][1]} → {s['hex']}")
        return 0
    if args.cmd == "build":
        out = build(Path(args.svg), Path(args.out), args.name)
        print(f"已寫入 {out}")
        return 0
    if args.cmd == "render":
        svg = Path(args.svg)
        png = render(svg, Path(args.out) if args.out else None)
        print(f"已截圖 {png}")
        if args.against:
            cmp_path = compare(Path(args.against), png, svg.with_suffix(".compare.png"))
            print(f"已產出並排比對圖 {cmp_path}")
        return 0
    raise SvgTraceError(f"子命令尚未實作: {args.cmd}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="svgtrace", description="圖片臨摹成可編輯簡報圖案")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("grab", help="從剪貼簿取圖存檔")
    g.add_argument("--out", help="輸出 png 路徑; 省略時開新的工作資料夾")

    pa = sub.add_parser("palette", help="取原圖主色")
    pa.add_argument("image", help="原圖路徑")
    pa.add_argument("--n", type=int, default=12, help="要取幾個主色, 預設 12")
    pa.add_argument("--at", action="append", default=[], metavar="X,Y",
                    help="指定座標精確取樣, 可重複")

    r = sub.add_parser("render", help="把 SVG 截圖")
    r.add_argument("svg", help="SVG 路徑")
    r.add_argument("--against", help="原圖路徑; 給了就順便產並排比對圖")
    r.add_argument("--out", help="輸出 png 路徑")

    b = sub.add_parser("build", help="SVG 轉成簡報裡的原生圖案")
    b.add_argument("svg", help="SVG 路徑")
    b.add_argument("--out", required=True, help="輸出 pptx 路徑; 已存在就追加一頁")
    b.add_argument("--name", help="圖案在簡報裡的名字, 預設用 SVG 檔名")

    args = p.parse_args(argv)
    try:
        return _dispatch(args)
    except SvgTraceError as e:
        print(f"錯誤: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
