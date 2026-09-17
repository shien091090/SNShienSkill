"""svgtrace — 把一張圖臨摹成 SVG, 再轉成 PowerPoint 原生可編輯圖案。

四個子命令:
    grab     從剪貼簿取圖存檔
    palette  取原圖主色與指定座標的顏色
    render   用 Chrome headless 把 SVG 截圖, 可與原圖並排比對
    build    驗證 SVG 並轉成簡報裡的原生圖案 (新建或追加一頁)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from lxml import etree
from pptx import Presentation
from pptx.util import Inches

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))

from svg_to_pptx import ConvertContext, EMU_PER_PX, collect_defs, convert_element
from svg_to_pptx.drawingml_converter import _collect_unsupported_visuals
from svg_to_pptx.drawingml_utils import SVG_NS

MARGIN_IN = 0.5
DEFAULT_W_IN, DEFAULT_H_IN = 13.333, 7.5

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


def _dispatch(args: argparse.Namespace) -> int:
    if args.cmd == "build":
        out = build(Path(args.svg), Path(args.out), args.name)
        print(f"已寫入 {out}")
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
