# svg-trace 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 做出 `svg-trace` skill — 給一張圖, AI 用 SVG 重現它, 轉成 PowerPoint 原生可編輯圖案輸出成 pptx。

**Architecture:** 單一 CLI 腳本 `scripts/svgtrace.py` 提供四個子命令 (`grab` `palette` `render` `build`), AI 在對話中依序呼叫它們完成臨摹流程。SVG 轉 DrawingML 的重活交給從 deck-pipeline 複製過來的 vendor code, 本腳本只負責取圖、取色、渲染比對、置入投影片。

**Tech Stack:** Python 3 (`py -3`)、python-pptx (含 lxml 與 Pillow)、Chrome/Edge headless、Windows PowerShell (剪貼簿)、pytest。

**Spec:** `~/.claude/skills/svg-trace/docs/2026-09-17-svg-trace-design.md`

## Global Constraints

- 指令一律寫 `py -3`, **不寫死版本號**。這台機器只有 Python 3.14, deck-pipeline 寫死 `py -3.12-64` 已經是壞的
- 相依只有 `py -3 -m pip install python-pptx pytest`。python-pptx 會帶進 lxml 與 Pillow。**不需要 pyyaml**
- 所有使用者看得到的訊息用**繁體中文**, 半形逗號風格比照 deck-pipeline
- 所有錯誤走 `SvgTraceError`, 由 `main()` 捕捉後印一行訊息並回傳 1。**不吐 traceback**
- 投影片邊界固定 `MARGIN_IN = 0.5` 吋; 新建檔尺寸 13.333 x 7.5 吋
- SVG 的 viewBox 寬度基準 1184 (= 12.333 吋 x 96)
- 測試檔 import 方式比照 deck-pipeline: `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` 後 `import svgtrace as st`
- commit 格式照 `~/.claude/rules/commit-format.md`: `[前綴] [svg-trace] 內容`, 單行標題不寫 body, **內容不出現英文程式碼識別字**
- 每個 task 結束都要 commit, 且 `git add` 只帶該 task 的檔案; commit 前跑一次不帶 pathspec 的 `git status --short` 確認 staging 乾淨 (工作區有使用者自己的 `settings.json` 與 `skills/synced/` 改動, 不可誤帶)

## File Structure

```
~/.claude/skills/svg-trace/
  SKILL.md                      觸發詞、七步流程、給 AI 的操作說明          (Task 8)
  docs/2026-09-17-svg-trace-design.md   設計文件 (已存在)
  docs/2026-09-18-svg-trace-plan.md     本計畫 (已存在)
  references/svg-rules.md       SVG 撰寫規則: viewBox 換算、支援子集、分群慣例 (Task 8)
  scripts/svgtrace.py           唯一入口, 四個子命令                      (Task 1~7)
  scripts/vendor/svg_to_pptx/   從 deck-pipeline 複製的轉換器              (Task 1)
  scripts/tests/__init__.py                                              (Task 1)
  scripts/tests/test_svgtrace.py                                         (Task 1~7)
```

**為什麼 `svgtrace.py` 是單一檔案而不拆模組**: 比照 deck-pipeline 的 `build_pptx.py` (單檔約 400 行) 這個既有慣例。四個子命令共用的只有 CLI 分發與錯誤型別, 拆檔會製造四個互不往來的小模組加一個膠水層, 沒有換到可讀性。完成後預估 300~350 行, 仍在單檔可掌握的範圍。

**`svgtrace.py` 的區塊順序** (讓後面的 task 知道自己的程式碼該插在哪):

1. docstring、import、常數、`SvgTraceError`
2. 幾何: `svg_size_px` `fit_box` (Task 2)
3. 驗證: `svg_problems` (Task 3)
4. 產檔: `_blank_layout` `_add_blank_slide` `svg_group` `build` (Task 4)
5. 取色: `palette` (Task 5)
6. 渲染: `find_chrome` `chrome_available` `render` `compare` (Task 6)
7. 剪貼簿: `work_dir` `grab` (Task 7)
8. CLI: `_dispatch` `main` (Task 1 建立骨架, 每個 task 補自己那支分支)

---

### Task 1: 骨架與轉換器複製

**Files:**
- Create: `~/.claude/skills/svg-trace/scripts/svgtrace.py`
- Create: `~/.claude/skills/svg-trace/scripts/vendor/svg_to_pptx/` (整包複製)
- Create: `~/.claude/skills/svg-trace/scripts/tests/__init__.py`
- Create: `~/.claude/skills/svg-trace/scripts/tests/test_svgtrace.py`
- Modify: `~/.claude/skills/deck-pipeline/scripts/vendor/svg_to_pptx/VENDOR.md`

**Interfaces:**
- Consumes: 無 (第一個 task)
- Produces: `SvgTraceError(Exception)`、`main(argv: list[str] | None = None) -> int`、`_dispatch(args) -> int`、模組常數 `MARGIN_IN = 0.5`、`DEFAULT_W_IN = 13.333`、`DEFAULT_H_IN = 7.5`。後續每個 task 都在 `_dispatch` 裡補自己的分支

- [ ] **Step 1: 確認相依裝好**

```bash
py -3 -m pip install python-pptx pytest
py -3 -c "import pptx, lxml, PIL; print('ok', pptx.__version__)"
```

預期: 印出 `ok 1.0.2` 或更新版本。

- [ ] **Step 2: 複製轉換器**

```bash
mkdir -p ~/.claude/skills/svg-trace/scripts
cp -r ~/.claude/skills/deck-pipeline/scripts/vendor ~/.claude/skills/svg-trace/scripts/vendor
ls ~/.claude/skills/svg-trace/scripts/vendor/svg_to_pptx/
```

預期: 列出 `drawingml_converter.py` 等 8 個 .py 加 `LICENSE` 與 `VENDOR.md`。

- [ ] **Step 3: 兩份 VENDOR.md 都加註雙份維護**

在 `~/.claude/skills/svg-trace/scripts/vendor/svg_to_pptx/VENDOR.md` 末尾加一行:

```
# 此包另有一份在 ~/.claude/skills/deck-pipeline/scripts/vendor/svg_to_pptx/, 上游更新時兩邊一起更新。
```

在 `~/.claude/skills/deck-pipeline/scripts/vendor/svg_to_pptx/VENDOR.md` 末尾加一行:

```
# 此包另有一份在 ~/.claude/skills/svg-trace/scripts/vendor/svg_to_pptx/, 上游更新時兩邊一起更新。
```

- [ ] **Step 4: 寫失敗的測試**

建立 `scripts/tests/__init__.py` (空檔) 與 `scripts/tests/test_svgtrace.py`:

```python
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import svgtrace as st  # noqa: E402


def test_no_subcommand_exits_2():
    with pytest.raises(SystemExit) as exc:
        st.main([])
    assert exc.value.code == 2


def test_error_is_reported_without_traceback(capsys, monkeypatch):
    def boom(args):
        raise st.SvgTraceError("測試用錯誤")

    monkeypatch.setattr(st, "_dispatch", boom)
    code = st.main(["palette", "x.png"])
    assert code == 1
    assert "測試用錯誤" in capsys.readouterr().err
```

- [ ] **Step 5: 跑測試確認失敗**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: FAIL, `ModuleNotFoundError: No module named 'svgtrace'`。

- [ ] **Step 6: 寫最小實作**

建立 `scripts/svgtrace.py`:

```python
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
```

- [ ] **Step 7: 跑測試確認通過**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: 2 passed。

- [ ] **Step 8: Commit**

```bash
cd ~/.claude && git status --short
git add skills/svg-trace/scripts skills/deck-pipeline/scripts/vendor/svg_to_pptx/VENDOR.md
git commit -m "[feat] [svg-trace] 1.建立指令骨架與四個子命令的參數解析 2.複製簡報圖案轉換器並在兩邊註記雙份維護"
```

---

### Task 2: 尺寸解析與等比置中

**Files:**
- Modify: `~/.claude/skills/svg-trace/scripts/svgtrace.py` (區塊 2)
- Test: `~/.claude/skills/svg-trace/scripts/tests/test_svgtrace.py`

**Interfaces:**
- Consumes: `SvgTraceError` (Task 1)
- Produces:
  - `svg_size_px(svg_path: Path) -> tuple[float, float]` — SVG 的像素寬高
  - `fit_box(vw_px: float, vh_px: float, box: tuple[float, float, float, float]) -> tuple[float, float, float, float]` — box 與回傳值都是 `(x, y, w, h)` 英吋
  - `_px(value: str) -> float`

- [ ] **Step 1: 寫失敗的測試**

加進 `tests/test_svgtrace.py`:

```python
def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_svg_size_from_viewbox(tmp_path):
    p = _write(tmp_path, "a.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1184 666"/>')
    assert st.svg_size_px(p) == (1184.0, 666.0)


def test_svg_size_falls_back_to_width_height(tmp_path):
    p = _write(tmp_path, "b.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="320"/>')
    assert st.svg_size_px(p) == (640.0, 320.0)


def test_svg_size_strips_units(tmp_path):
    p = _write(tmp_path, "c.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="640px" height="320px"/>')
    assert st.svg_size_px(p) == (640.0, 320.0)


def test_svg_size_without_any_size_raises(tmp_path):
    p = _write(tmp_path, "d.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')
    with pytest.raises(st.SvgTraceError, match="viewBox"):
        st.svg_size_px(p)


def test_svg_size_parse_error_raises(tmp_path):
    p = _write(tmp_path, "e.svg", "<svg><unclosed>")
    with pytest.raises(st.SvgTraceError, match="解析失敗"):
        st.svg_size_px(p)


def test_svg_size_missing_file_raises(tmp_path):
    with pytest.raises(st.SvgTraceError, match="檔案不存在"):
        st.svg_size_px(tmp_path / "nope.svg")


def test_fit_box_height_limited():
    # 1184x666 塞進 12.333 x 6.5 吋: 高度先撞牆, 高吃滿 6.5, 寬按比例縮並水平置中
    x, y, w, h = st.fit_box(1184, 666, (0.5, 0.5, 12.333, 6.5))
    assert h == pytest.approx(6.5)
    assert w == pytest.approx(11.5556, abs=0.001)
    assert x == pytest.approx(0.8887, abs=0.001)
    assert y == pytest.approx(0.5)


def test_fit_box_width_limited():
    # 1184x400 塞進同一個 box: 寬度先撞牆, 寬吃滿 12.333, 高按比例縮並垂直置中
    x, y, w, h = st.fit_box(1184, 400, (0.5, 0.5, 12.333, 6.5))
    assert w == pytest.approx(12.333, abs=0.001)
    assert h == pytest.approx(4.1667, abs=0.001)
    assert x == pytest.approx(0.5)
    assert y == pytest.approx(1.6667, abs=0.001)
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: FAIL, `AttributeError: module 'svgtrace' has no attribute 'svg_size_px'`。

- [ ] **Step 3: 寫實作**

import 區加上:

```python
import re
from xml.etree import ElementTree as ET
```

在 `SvgTraceError` 後面加上區塊 2:

```python
def _px(value: str) -> float:
    """去掉 px / pt / % 之類的單位尾巴, 只留數字"""
    return float(re.sub(r"[a-z%]+$", "", value.strip()))


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
        _, _, vw, vh = (float(v) for v in vb.replace(",", " ").split())
        return vw, vh
    w, h = root.get("width"), root.get("height")
    if not w or not h:
        raise SvgTraceError(f"{svg_path.name} 沒有 viewBox 也沒有 width/height, 無法決定尺寸")
    return _px(w), _px(h)


def fit_box(vw_px: float, vh_px: float, box: tuple[float, float, float, float]):
    """把 vw_px x vh_px 的圖等比縮放置中塞進 box。box 與回傳值都是 (x, y, w, h) 英吋"""
    bx, by, bw, bh = box
    scale = min(bw / (vw_px / 96), bh / (vh_px / 96))
    gw, gh = (vw_px / 96) * scale, (vh_px / 96) * scale
    return bx + (bw - gw) / 2, by + (bh - gh) / 2, gw, gh
```

- [ ] **Step 4: 跑測試確認通過**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: 10 passed。

- [ ] **Step 5: Commit**

```bash
cd ~/.claude && git status --short
git add skills/svg-trace/scripts
git commit -m "[feat] [svg-trace] 實作向量圖尺寸解析與等比置中計算"
```

---

### Task 3: 向量圖驗證

**Files:**
- Modify: `~/.claude/skills/svg-trace/scripts/svgtrace.py` (區塊 3)
- Test: `~/.claude/skills/svg-trace/scripts/tests/test_svgtrace.py`

**Interfaces:**
- Consumes: Task 2 引入的 `ET`、`SvgTraceError` (Task 1)
- Produces: `svg_problems(svg_path: Path) -> list[str]` — 沒問題回空 list; 有問題回一到多則中文訊息

- [ ] **Step 1: 寫失敗的測試**

```python
SVG_OK = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">
  <rect x="10" y="10" width="100" height="50" fill="#2B579A"/>
  <text x="20" y="40" font-size="16" fill="#FFFFFF">框</text>
</svg>'''


def test_svg_problems_empty_for_supported_svg(tmp_path):
    p = _write(tmp_path, "ok.svg", SVG_OK)
    assert st.svg_problems(p) == []


def test_svg_problems_reports_unsupported_element(tmp_path):
    p = _write(tmp_path, "bad.svg",
               '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
               '<foreignObject width="1" height="1"/></svg>')
    problems = st.svg_problems(p)
    assert len(problems) == 1
    assert "foreignObject" in problems[0]


def test_svg_problems_reports_parse_error(tmp_path):
    p = _write(tmp_path, "broken.svg", "<svg><unclosed>")
    assert any("解析失敗" in m for m in st.svg_problems(p))
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: FAIL, `AttributeError: module 'svgtrace' has no attribute 'svg_problems'`。

- [ ] **Step 3: 寫實作**

import 區加上:

```python
from svg_to_pptx.drawingml_converter import _collect_unsupported_visuals
```

區塊 3:

```python
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
        return [f"SVG 含不支援元素 {svg_path.name}: {'; '.join(unsupported[:8])}"]
    return []
```

- [ ] **Step 4: 跑測試確認通過**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: 13 passed。

- [ ] **Step 5: Commit**

```bash
cd ~/.claude && git status --short
git add skills/svg-trace/scripts
git commit -m "[feat] [svg-trace] 實作向量圖驗證, 一次列出所有不支援的元素"
```

---

### Task 4: 產生簡報檔

**Files:**
- Modify: `~/.claude/skills/svg-trace/scripts/svgtrace.py` (區塊 4, 以及 `_dispatch` 補 build 分支)
- Test: `~/.claude/skills/svg-trace/scripts/tests/test_svgtrace.py`

**Interfaces:**
- Consumes: `svg_size_px` `fit_box` (Task 2)、`svg_problems` (Task 3)、`SvgTraceError` (Task 1)
- Produces:
  - `_blank_layout(prs)` / `_add_blank_slide(prs)`
  - `svg_group(slide, box: tuple[float, float, float, float], svg_path: Path, name: str) -> None`
  - `build(svg_path: Path, out_path: Path, name: str | None = None) -> Path` — 回傳寫出去的 pptx 路徑

- [ ] **Step 1: 寫失敗的測試**

測試檔頂端補 import:

```python
from pptx import Presentation
from pptx.util import Inches
```

測試:

```python
def test_build_creates_16_9_deck_when_missing(tmp_path):
    svg = _write(tmp_path, "d.svg", SVG_OK)
    out = tmp_path / "out.pptx"
    st.build(svg, out)
    prs = Presentation(str(out))
    assert prs.slide_width == Inches(13.333)
    assert prs.slide_height == Inches(7.5)
    assert len(prs.slides._sldIdLst) == 1


def test_build_appends_a_slide_to_existing_deck(tmp_path):
    svg = _write(tmp_path, "d.svg", SVG_OK)
    out = tmp_path / "out.pptx"
    st.build(svg, out, name="第一張")
    st.build(svg, out, name="第二張")
    slides = list(Presentation(str(out)).slides)
    assert len(slides) == 2
    # 原有那頁不可被動到
    assert [s.shapes[0].name for s in slides] == ["第一張", "第二張"]


def test_build_keeps_existing_slide_size(tmp_path):
    out = tmp_path / "four-three.pptx"
    Presentation().save(str(out))  # python-pptx 預設 10 x 7.5 吋
    svg = _write(tmp_path, "d.svg", SVG_OK)
    st.build(svg, out)
    after = Presentation(str(out))
    assert after.slide_width == Inches(10)
    assert after.slide_height == Inches(7.5)


def test_build_slide_has_only_the_diagram_group(tmp_path):
    svg = _write(tmp_path, "d.svg", SVG_OK)
    out = tmp_path / "out.pptx"
    st.build(svg, out, name="流程")
    slide = list(Presentation(str(out)).slides)[0]
    assert len(slide.shapes) == 1
    assert slide.shapes[0].name == "流程"


def test_build_shape_ids_do_not_collide(tmp_path):
    svg = _write(tmp_path, "d.svg", SVG_OK)
    out = tmp_path / "out.pptx"
    st.build(svg, out)
    st.build(svg, out)
    for slide in Presentation(str(out)).slides:
        ids = re.findall(r'<p:cNvPr id="(\d+)"', slide.shapes._spTree.xml)
        assert len(ids) == len(set(ids)), "同一頁裡的圖案編號重複了"


def test_build_refuses_unsupported_svg(tmp_path):
    svg = _write(tmp_path, "bad2.svg",
                 '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                 '<foreignObject width="1" height="1"/></svg>')
    with pytest.raises(st.SvgTraceError, match="foreignObject"):
        st.build(svg, tmp_path / "x.pptx")
    assert not (tmp_path / "x.pptx").exists(), "驗證沒過就不該產出半成品"


def test_build_reports_locked_file_in_chinese(tmp_path, monkeypatch):
    svg = _write(tmp_path, "d.svg", SVG_OK)

    def deny(self, path):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr("pptx.presentation.Presentation.save", deny)
    with pytest.raises(st.SvgTraceError, match="PowerPoint"):
        st.build(svg, tmp_path / "locked.pptx")
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: FAIL, `AttributeError: module 'svgtrace' has no attribute 'build'`。

- [ ] **Step 3: 寫實作**

import 區加上:

```python
from lxml import etree
from pptx import Presentation
from pptx.util import Inches

from svg_to_pptx import ConvertContext, EMU_PER_PX, collect_defs, convert_element
from svg_to_pptx.drawingml_utils import SVG_NS
```

常數區加上:

```python
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
```

區塊 4:

```python
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
```

`_dispatch` 改成:

```python
def _dispatch(args: argparse.Namespace) -> int:
    if args.cmd == "build":
        out = build(Path(args.svg), Path(args.out), args.name)
        print(f"已寫入 {out}")
        return 0
    raise SvgTraceError(f"子命令尚未實作: {args.cmd}")
```

- [ ] **Step 4: 跑測試確認通過**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: 20 passed。

- [ ] **Step 5: 手動驗一次產出的檔真的能開**

先寫一個小 SVG 到暫存路徑 (含 rect 與 text 即可), 然後:

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 svgtrace.py build <剛剛那個 svg> --out <暫存路徑>/manual.pptx
```

預期: 印出 `已寫入 ...`。用 PowerPoint 開起來確認: 只有一頁、頁上只有一個群組、進入群組後每個框與文字都能單獨選取與編輯。

- [ ] **Step 6: Commit**

```bash
cd ~/.claude && git status --short
git add skills/svg-trace/scripts
git commit -m "[feat] [svg-trace] 實作產生簡報檔, 支援新建與往既有簡報追加一頁"
```

---

### Task 5: 取色

**Files:**
- Modify: `~/.claude/skills/svg-trace/scripts/svgtrace.py` (區塊 5, 以及 `_dispatch` 補 palette 分支)
- Test: `~/.claude/skills/svg-trace/scripts/tests/test_svgtrace.py`

**Interfaces:**
- Consumes: `SvgTraceError` (Task 1)
- Produces:
  - `_hex(rgb) -> str`
  - `palette(img_path: Path, n: int = 12, at: list[str] = ()) -> dict`, 回傳
    `{"size": (w, h), "colors": [{"hex": "#RRGGBB", "ratio": float}, ...], "samples": [{"at": (x, y), "hex": "#RRGGBB"}, ...]}`,
    `colors` 依佔比由大到小排序

- [ ] **Step 1: 寫失敗的測試**

測試檔頂端補 import:

```python
from PIL import Image, ImageDraw
```

測試:

```python
def _two_tone_png(tmp_path):
    im = Image.new("RGB", (100, 50), "#EAF1FB")
    ImageDraw.Draw(im).rectangle([0, 0, 49, 49], fill="#2B579A")
    p = tmp_path / "src.png"
    im.save(p)
    return p


def test_palette_reports_size_and_dominant_colors(tmp_path):
    result = st.palette(_two_tone_png(tmp_path), n=8)
    assert result["size"] == (100, 50)
    hexes = [c["hex"] for c in result["colors"]]
    assert "#2B579A" in hexes
    assert "#EAF1FB" in hexes
    assert sum(c["ratio"] for c in result["colors"]) == pytest.approx(1.0, abs=0.001)


def test_palette_samples_exact_pixels(tmp_path):
    result = st.palette(_two_tone_png(tmp_path), at=["10,10", "80,10"])
    assert [s["hex"] for s in result["samples"]] == ["#2B579A", "#EAF1FB"]


def test_palette_rejects_out_of_range_point(tmp_path):
    with pytest.raises(st.SvgTraceError, match="超出圖片範圍"):
        st.palette(_two_tone_png(tmp_path), at=["999,999"])


def test_palette_missing_file_raises(tmp_path):
    with pytest.raises(st.SvgTraceError, match="圖片不存在"):
        st.palette(tmp_path / "nope.png")
```

注意測試用關鍵字 `at=` 呼叫, 所以實作的參數名就叫 `at`, 與 CLI 的 `--at` 一致。

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: FAIL, `AttributeError: module 'svgtrace' has no attribute 'palette'`。

- [ ] **Step 3: 寫實作**

import 區加上:

```python
from PIL import Image, ImageDraw
```

區塊 5:

```python
def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(rgb)


def palette(img_path: Path, n: int = 12, at: list[str] = ()) -> dict:
    """取原圖的主色與指定座標的精確顏色。

    量化只回答「這張圖大致有哪些色」, 但「那條線是什麼藍」要靠 at 點名問。
    """
    if not img_path.exists():
        raise SvgTraceError(f"圖片不存在: {img_path}")
    im = Image.open(img_path).convert("RGB")

    quantized = im.quantize(colors=max(2, n))
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
```

`_dispatch` 補分支 (放在 build 分支前後都可以):

```python
    if args.cmd == "palette":
        result = palette(Path(args.image), args.n, args.at)
        print(f"尺寸 {result['size'][0]}x{result['size'][1]}")
        for c in result["colors"]:
            print(f"  {c['hex']}  {c['ratio'] * 100:5.1f}%")
        for s in result["samples"]:
            print(f"  取樣 {s['at'][0]},{s['at'][1]} → {s['hex']}")
        return 0
```

- [ ] **Step 4: 跑測試確認通過**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: 24 passed。

- [ ] **Step 5: Commit**

```bash
cd ~/.claude && git status --short
git add skills/svg-trace/scripts
git commit -m "[feat] [svg-trace] 實作取色, 輸出主色佔比與指定座標的精確顏色"
```

---

### Task 6: 瀏覽器截圖與並排比對

**Files:**
- Modify: `~/.claude/skills/svg-trace/scripts/svgtrace.py` (區塊 6, 以及 `_dispatch` 補 render 分支)
- Test: `~/.claude/skills/svg-trace/scripts/tests/test_svgtrace.py`

**Interfaces:**
- Consumes: `svg_size_px` (Task 2)、`SvgTraceError` (Task 1)、`Image` `ImageDraw` (Task 5 引入)
- Produces:
  - 模組常數 `CHROME_CANDIDATES: tuple[str, ...]`、`GUTTER_PX = 16`、`LABEL_PX = 24`
  - `find_chrome() -> Path`
  - `chrome_available() -> bool`
  - `render(svg_path: Path, out_path: Path | None = None) -> Path` — 省略 out 時存成 `<svg檔名>.render.png`
  - `compare(original: Path, trace_png: Path, out_path: Path) -> Path`

- [ ] **Step 1: 寫失敗的測試**

```python
def test_find_chrome_prefers_env_var(tmp_path, monkeypatch):
    fake = tmp_path / "chrome.exe"
    fake.write_bytes(b"")
    monkeypatch.setenv("CHROME", str(fake))
    assert st.find_chrome() == fake


def test_find_chrome_lists_tried_paths_when_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("CHROME", raising=False)
    monkeypatch.setattr(st, "CHROME_CANDIDATES", (str(tmp_path / "nope.exe"),))
    with pytest.raises(st.SvgTraceError, match="找不到 Chrome"):
        st.find_chrome()


def test_compare_puts_two_images_side_by_side(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    Image.new("RGB", (100, 50), "#FF0000").save(a)
    Image.new("RGB", (100, 50), "#00FF00").save(b)
    im = Image.open(st.compare(a, b, tmp_path / "cmp.png"))
    assert im.width == 100 + st.GUTTER_PX + 100
    assert im.height == 50 + st.LABEL_PX


def test_compare_scales_to_equal_height(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    Image.new("RGB", (100, 50), "#FF0000").save(a)
    Image.new("RGB", (200, 200), "#00FF00").save(b)
    im = Image.open(st.compare(a, b, tmp_path / "cmp2.png"))
    # 兩張都拉到 200 高: 原圖變 400 寬, 臨摹圖維持 200 寬
    assert im.width == 400 + st.GUTTER_PX + 200
    assert im.height == 200 + st.LABEL_PX


@pytest.mark.skipif(not st.chrome_available(), reason="這台機器沒有 Chrome 或 Edge")
def test_render_produces_a_png(tmp_path):
    svg = _write(tmp_path, "r.svg", SVG_OK)
    out = st.render(svg)
    assert out.exists() and out.stat().st_size > 0
    assert Image.open(out).size == (400, 200)
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: 收集階段就 FAIL, `AttributeError: module 'svgtrace' has no attribute 'chrome_available'` (因為 `skipif` 在 import 時就會求值)。

- [ ] **Step 3: 寫實作**

import 區加上:

```python
import os
import subprocess
```

常數區加上:

```python
CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)
GUTTER_PX = 16
LABEL_PX = 24
```

區塊 6:

```python
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
```

`_dispatch` 補分支:

```python
    if args.cmd == "render":
        svg = Path(args.svg)
        png = render(svg, Path(args.out) if args.out else None)
        print(f"已截圖 {png}")
        if args.against:
            cmp_path = compare(Path(args.against), png, svg.with_suffix(".compare.png"))
            print(f"已產出並排比對圖 {cmp_path}")
        return 0
```

- [ ] **Step 4: 跑測試確認通過**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: 29 passed (這台機器有 Chrome, 所以那題不會 skip)。

- [ ] **Step 5: Commit**

```bash
cd ~/.claude && git status --short
git add skills/svg-trace/scripts
git commit -m "[feat] [svg-trace] 1.實作瀏覽器截圖 2.實作原圖與臨摹圖並排比對"
```

---

### Task 7: 剪貼簿取圖

**Files:**
- Modify: `~/.claude/skills/svg-trace/scripts/svgtrace.py` (區塊 7, 以及 `_dispatch` 補 grab 分支)
- Test: `~/.claude/skills/svg-trace/scripts/tests/test_svgtrace.py`

**Interfaces:**
- Consumes: `SvgTraceError` (Task 1)、`subprocess` (Task 6 引入)
- Produces:
  - 模組常數 `PS_GRAB: str`
  - `work_dir() -> Path` — 回傳 `~/svg-trace/<yyyymmdd-hhmmss>/` 並建好
  - `grab(out_path: Path) -> Path`

- [ ] **Step 1: 寫失敗的測試**

```python
class _FakeProc:
    def __init__(self, returncode, stderr=""):
        self.returncode = returncode
        self.stdout = ""
        self.stderr = stderr


def test_grab_reports_empty_clipboard(tmp_path, monkeypatch):
    monkeypatch.setattr(st.subprocess, "run", lambda *a, **k: _FakeProc(3))
    with pytest.raises(st.SvgTraceError, match="剪貼簿沒有圖片"):
        st.grab(tmp_path / "out.png")


def test_grab_reports_other_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(st.subprocess, "run", lambda *a, **k: _FakeProc(1, "存取被拒"))
    with pytest.raises(st.SvgTraceError, match="取剪貼簿影像失敗"):
        st.grab(tmp_path / "out.png")


def test_grab_returns_path_on_success(tmp_path, monkeypatch):
    target = tmp_path / "sub" / "out.png"

    def fake_run(*a, **k):
        target.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 10), "#FFFFFF").save(target)
        return _FakeProc(0)

    monkeypatch.setattr(st.subprocess, "run", fake_run)
    assert st.grab(target) == target


def test_work_dir_is_timestamped_under_home(tmp_path, monkeypatch):
    monkeypatch.setattr(st.Path, "home", staticmethod(lambda: tmp_path))
    d = st.work_dir()
    assert d.exists()
    assert d.parent == tmp_path / "svg-trace"
    assert re.fullmatch(r"\d{8}-\d{6}", d.name)
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: FAIL, `AttributeError: module 'svgtrace' has no attribute 'grab'`。

- [ ] **Step 3: 寫實作**

import 區加上:

```python
from datetime import datetime
```

常數區加上 (注意這是 `.format()` 樣板, 所以 PowerShell 的大括號要寫成雙層):

```python
PS_GRAB = '''
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$img = [System.Windows.Forms.Clipboard]::GetImage()
if ($null -eq $img) {{ exit 3 }}
$img.Save("{out}", [System.Drawing.Imaging.ImageFormat]::Png)
Write-Output "$($img.Width)x$($img.Height)"
'''
```

區塊 7:

```python
def work_dir() -> Path:
    """走剪貼簿時沒有「原圖旁邊」可言, 所以開一個帶時間戳的工作資料夾"""
    d = Path.home() / "svg-trace" / datetime.now().strftime("%Y%m%d-%H%M%S")
    d.mkdir(parents=True, exist_ok=True)
    return d


def grab(out_path: Path) -> Path:
    """從 Windows 剪貼簿取影像存成 PNG。使用者截圖後完全不必碰路徑"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    script = PS_GRAB.format(out=str(out_path).replace("\\", "\\\\"))
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-STA", "-Command", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode == 3:
        raise SvgTraceError("剪貼簿沒有圖片。請先截圖 (Win+Shift+S), 或直接給我圖片路徑")
    if proc.returncode != 0 or not out_path.exists():
        raise SvgTraceError(f"取剪貼簿影像失敗: {proc.stderr.strip()[:200]}")
    return out_path
```

`_dispatch` 補分支:

```python
    if args.cmd == "grab":
        out = Path(args.out) if args.out else work_dir() / "source.png"
        print(f"已存檔 {grab(out)}")
        return 0
```

`_dispatch` 到這裡四個分支都齊了, 最後那行 `raise SvgTraceError(f"子命令尚未實作: {args.cmd}")` 保留當防呆。

- [ ] **Step 4: 跑測試確認通過**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/test_svgtrace.py -v
```

預期: 33 passed。

- [ ] **Step 5: 實機驗一次剪貼簿真的通**

先手動截一張圖 (Win+Shift+S), 然後:

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 svgtrace.py grab --out <暫存路徑>/clip.png
```

預期: 印出 `已存檔 ...`, 且該檔打得開、就是剛剛截的那張。

注意: 剪貼簿裡沒有影像時會回 `錯誤: 剪貼簿沒有圖片...` 並以 1 退出, 這是正常的錯誤路徑, 不是失敗。

- [ ] **Step 6: Commit**

```bash
cd ~/.claude && git status --short
git add skills/svg-trace/scripts
git commit -m "[feat] [svg-trace] 實作從剪貼簿取圖存檔"
```

---

### Task 8: 使用說明、撰寫規則與冷跑驗證

**Files:**
- Create: `~/.claude/skills/svg-trace/SKILL.md`
- Create: `~/.claude/skills/svg-trace/references/svg-rules.md`

**Interfaces:**
- Consumes: 四個子命令全部 (Task 1~7)
- Produces: 可被 Claude Code 載入並觸發的 skill

- [ ] **Step 1: 寫 `references/svg-rules.md`**

內容必須涵蓋:

- **viewBox 換算**: 一律 `viewBox="0 0 1184 <等比高>"`, 1184 = 12.333 吋 x 96。原圖非 16:9 時以寬度為準等比推高度; 推出來的高度超過 624 (= 6.5 吋 x 96) 時改以高度為準回推寬度
- **支援的語法子集**: `rect` `circle` `ellipse` `line` `polyline` `polygon` `path` `text` `tspan` `g` `marker` (箭頭)、`stroke-dasharray` (虛線)、線性與放射漸層
- **不支援**: `foreignObject`、濾鏡、外部圖片。`build` 會擋下來並列出
- **分群慣例**: 用 `<g id="...">` 分群, 依**語意**分而不是依畫的順序。使用者要進 PowerPoint 改, 群組分得有道理才好選取
- **文字**: 用 `text` 搭 `text-anchor` 對齊, 不要靠空白排版。`font-size` 直接寫數字, 等同 pptx 裡的像素
- **刻意簡化**: 陰影、雜訊材質、手繪抖動一律不畫; 複雜漸層退成單色或兩段漸層。理由是使用者要的是進 PowerPoint 改, 這些東西只會礙事

- [ ] **Step 2: 寫 `SKILL.md`**

frontmatter 直接照抄這份, 不要自己重寫 (觸發準確度全靠 `description`):

```yaml
---
name: svg-trace
description: 觸發詞「描圖」或 /svg-trace [圖片路徑]。給一張圖 (截圖、別人簡報裡的示意圖、網路上的架構圖), 用 SVG 盡可能重現它, 再轉成 PowerPoint 原生可編輯圖案輸出成 pptx, 供使用者進 PowerPoint 換文字換配色併進自己的簡報。圖可以走剪貼簿 (截圖後直接說「描圖」, 不必給路徑)、檔案路徑、或貼進對話。使用者說要描圖、臨摹這張圖、把這張圖變成可編輯的、重畫成 PPT 圖案、想把圖轉成可以改的向量圖案時使用。
---
```

正文要寫的:

1. **取得圖檔**的三種方式與優先序: 剪貼簿 (推薦) / 圖片路徑 / 貼進對話。**貼進對話時仍要順手跑一次 `grab`** — 使用者既然貼得出來, 圖多半還在剪貼簿裡, 撈到就升級成完整流程, 撈不到才退化成沒有取色與並排比對的目視模式
2. **分流**: 看圖先講一句適合度評估。照片與複雜插畫要明說「SVG 重現效果會很差, 建議直接貼圖」, 但使用者堅持就照做, **不勸第二次**
3. **七步流程**, 每步寫出實際指令
4. **自我校正迴圈上限 3 輪**, 每輪回報一句「這輪修了什麼」讓使用者看得出是在收斂還是原地打轉; 提早收斂就提早結束, 不必跑滿
5. **產物位置**: 有給路徑就放原圖旁邊 (`<原檔名>.svg` `<原檔名>.compare.png` `<原檔名>.pptx`); 走剪貼簿就放工作資料夾 (`source.png` `trace.svg` `compare.png` `trace.pptx`)
6. **相依**: `py -3 -m pip install python-pptx` 加 Chrome 或 Edge。指令一律寫 `py -3`
7. **常見失敗**: 簡報被 PowerPoint 開著要先關掉再重跑; 找不到 Chrome 可設 `CHROME` 環境變數指到執行檔

- [ ] **Step 3: 跑全部測試**

```bash
cd ~/.claude/skills/svg-trace/scripts && py -3 -m pytest tests/ -v
```

預期: 33 passed。

- [ ] **Step 4: 冷跑驗證**

依 `~/.claude/rules/memory-policy.md` 第六節, skill 定案前要在沒用過的工作目錄下冷跑, 等同模擬一台新機器。在一個全新的暫存目錄下:

```bash
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 py -3 ~/.claude/skills/svg-trace/scripts/svgtrace.py palette <任一張圖>
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 py -3 ~/.claude/skills/svg-trace/scripts/svgtrace.py build <任一 svg> --out cold.pptx
```

預期: 兩個指令都能在陌生工作目錄下正常跑完, 不依賴任何 memory、也不依賴當前目錄。

- [ ] **Step 5: memory 汙染清查**

依 `~/.claude/rules/memory-policy.md` 第六節, 掃所有 memory 目錄:

```bash
ls ~/.claude/projects/*/memory/
```

與這個 skill 相關的內容: 執行需要的搬進 `SKILL.md`, 跨專案通則搬進 `~/.claude/rules/`。搬完刪掉對應的 memory 檔與 `MEMORY.md` 索引行, 並回報搬了什麼、刪了什麼。

- [ ] **Step 6: Commit**

```bash
cd ~/.claude && git status --short
git add skills/svg-trace
git commit -m "[docs] [svg-trace] 撰寫使用說明與向量圖撰寫規則"
```

---

## 附帶收尾 (不屬於本 skill, 同一輪順手修掉)

deck-pipeline 的 `SKILL.md` 把指令寫死成 `py -3.12-64`, 但這台機器只有 Python 3.14, 照著抄會直接失敗 (`No suitable Python runtime found`)。

- [ ] **Step 1: 改掉寫死的版本**

把 `~/.claude/skills/deck-pipeline/SKILL.md` 裡所有 `py -3.12-64` 改成 `py -3` (第 108、114 行附近各一處, 以實際搜尋結果為準)。

- [ ] **Step 2: 確認 deck-pipeline 沒被改壞**

```bash
cd ~/.claude/skills/deck-pipeline/scripts && py -3 -m pytest tests/ -v
```

預期: 39 passed。

- [ ] **Step 3: Commit**

```bash
cd ~/.claude && git status --short
git add skills/deck-pipeline/SKILL.md
git commit -m "[fix] [deck-pipeline] 修正指令寫死不存在的直譯器版本導致無法執行"
```
