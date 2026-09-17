"""svgtrace — 把一張圖臨摹成 SVG, 再轉成 PowerPoint 原生可編輯圖案。

四個子命令:
    grab     從剪貼簿取圖存檔
    palette  取原圖主色與指定座標的顏色
    render   用 Chrome headless 把 SVG 截圖, 可與原圖並排比對
    build    驗證 SVG 並轉成簡報裡的原生圖案 (新建或追加一頁)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))

MARGIN_IN = 0.5
DEFAULT_W_IN, DEFAULT_H_IN = 13.333, 7.5


class SvgTraceError(Exception):
    """使用者看得懂的錯誤。main() 捕捉後印一行訊息並回傳 1, 不吐 traceback。"""


def _dispatch(args: argparse.Namespace) -> int:
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
