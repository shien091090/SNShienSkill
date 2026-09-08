# deck-pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可重複使用的 Claude Code skill `deck-pipeline`, 把未整理的簡報素材資料夾一路帶到可編輯 pptx。

**Architecture:** 一份 SKILL.md 定義六階段流程規則 (collect → organize → script → slides → style → build), 兩份 references 放格式規格與版型定案細節, 一支 `scripts/build_pptx.py` 把 SLIDES.md + STYLE.md 轉成 pptx。狀態靠工作資料夾內的 STATUS.md 銜接, 不用外部 orchestration。

**Tech Stack:** Python 3.12 (`py -3.12-64`), python-pptx, PyYAML, Pillow (python-pptx 相依, 直接用), pytest。Claude Code 內建 `design` skill 用於階段 5。

**Spec:** `C:\Users\lithoshu\.claude\skills\deck-pipeline\docs\2026-09-07-deck-pipeline-design.md`

## Global Constraints

- skill 根目錄: `C:\Users\lithoshu\.claude\skills\deck-pipeline\` (以下用 `<skill>` 代稱); 不是 git repo, 每個 task 結尾以驗證步驟取代 commit
- Python 一律 `py -3.12-64`; 機器預設 python 3.8 不可用
- 投影片 16:9, 13.333 x 7.5 英吋; `box` 單位英吋 `[x, y, w, h]`
- 版型初始字彙: `title` `section` `text` `image` `image-text` `compare`
- 元素 role 字彙: `title` `subtitle` `body` `image` `left` `right`
- 圖片路徑 `TODO` = 待補圖, 畫灰框 (#D1D5DB) 印描述
- 所有文件與 skill 內文一律繁體中文, 半形逗號
- 互動全部純文字對話, 不用 AskUserQuestion
- 所有素材必須是資料夾內的檔案

---

## File Structure

```
<skill>/
  SKILL.md                         流程總則 (Task 8)
  references/
    formats.md                     STATUS / SLIDES / IMAGES_TODO / STYLE 格式 (Task 6)
    stage-style.md                 階段 5 細節 (Task 7)
  scripts/
    build_pptx.py                  parse_slides / parse_style / validate / render / images_todo / main (Task 2~5)
    tests/
      test_build_pptx.py           pytest (Task 2~5)
  examples/mini-deck/              smoke test 資料 (Task 1)
    STATUS.md
    SLIDES.md
    STYLE.md
    01_背景/flow_old.png
    02_做法/
  docs/
    2026-09-07-deck-pipeline-design.md   (已存在)
    2026-09-07-deck-pipeline-plan.md     (本文件)
```

`build_pptx.py` 單一模組, 責任切成五個純函式 + main, 測試直接 import。

---

### Task 1: 環境與 mini-deck 範例

**Files:**
- Create: `<skill>/examples/mini-deck/STATUS.md`
- Create: `<skill>/examples/mini-deck/SLIDES.md`
- Create: `<skill>/examples/mini-deck/STYLE.md`
- Create: `<skill>/examples/mini-deck/01_背景/flow_old.png`
- Create: `<skill>/examples/mini-deck/02_做法/.gitkeep`
- Create: `<skill>/scripts/tests/__init__.py` (空檔)

**Interfaces:**
- Produces: mini-deck 資料夾, 後續 Task 4/5/9 的測試與 smoke test 都吃它

- [ ] **Step 1: 安裝相依**

```powershell
py -3.12-64 -m pip install python-pptx pyyaml pytest
py -3.12-64 -c "import pptx, yaml, PIL, pytest; print(pptx.__version__, yaml.__version__, PIL.__version__)"
```

Expected: 印出三個版本號, 無 ModuleNotFoundError

- [ ] **Step 2: 建資料夾**

```powershell
$s = "$env:USERPROFILE\.claude\skills\deck-pipeline"
New-Item -ItemType Directory -Force "$s\references", "$s\scripts\tests", "$s\examples\mini-deck\01_背景", "$s\examples\mini-deck\02_做法" | Out-Null
New-Item -ItemType File -Force "$s\scripts\tests\__init__.py", "$s\examples\mini-deck\02_做法\.gitkeep" | Out-Null
```

- [ ] **Step 3: 產一張測試用 png**

```powershell
py -3.12-64 -c "from PIL import Image; Image.new('RGB',(400,300),(37,99,235)).save(r'$env:USERPROFILE\.claude\skills\deck-pipeline\examples\mini-deck\01_背景\flow_old.png')"
```

- [ ] **Step 4: 寫 mini-deck/SLIDES.md**

```markdown
# mini-deck 範例

## 01 背景

### [title] 為什麼要做這件事
把散亂素材變成一份簡報

### [text] 現況三個痛點
- 素材散在各處
- 講稿與頁面混在一起
- 排版每次從零開始

> 講稿對應: 背景第一段

### [image] 目前的流程長這樣
![舊流程截圖](01_背景/flow_old.png)
- 每一步都是手動

## 02 做法

### [section] 做法

### [image-text] 理想的樣子
![描述: 一張簡化的箭頭圖, 三步變一步](TODO)
- 六階段
- 一個資料夾
- 一份 pptx

### [compare] 舊 vs 新
| 舊 | 新 |
| 手動搬檔 | AI 分類 |
| 邊寫邊排 | 先講稿再頁面 |
```

- [ ] **Step 5: 寫 mini-deck/STYLE.md**

````markdown
# mini-deck 版型

## 人讀描述

白底深灰字, 藍色強調。六種版型:
- title: 大標居中偏上, 副標在下
- section: 章節名置中
- text: 標題在上, 條列佔中間大區
- image: 標題在上, 圖佔中間, 底部一行註解
- image-text: 左圖右文
- compare: 標題在上, 左右兩欄

## 腳本設定

```yaml
slide: {w: 13.333, h: 7.5}
theme:
  bg: "#FFFFFF"
  fg: "#1F2937"
  accent: "#2563EB"
  font_title: "Noto Sans TC"
  font_body: "Noto Sans TC"
layouts:
  title:
    - {role: title,    box: [1.0, 2.4, 11.3, 1.4], size: 40, bold: true}
    - {role: subtitle, box: [1.0, 4.0, 11.3, 1.0], size: 22}
  section:
    - {role: title,    box: [1.0, 3.0, 11.3, 1.4], size: 36, bold: true, color: "#2563EB"}
  text:
    - {role: title,    box: [0.8, 0.6, 11.7, 1.2], size: 32, bold: true}
    - {role: body,     box: [0.8, 2.2, 11.7, 4.5], size: 20}
  image:
    - {role: title,    box: [0.8, 0.5, 11.7, 1.0], size: 28, bold: true}
    - {role: image,    box: [0.8, 1.8, 11.7, 4.6]}
    - {role: body,     box: [0.8, 6.6, 11.7, 0.6], size: 16}
  image-text:
    - {role: title,    box: [0.8, 0.5, 11.7, 1.0], size: 28, bold: true}
    - {role: image,    box: [0.8, 1.8, 6.0, 4.8]}
    - {role: body,     box: [7.2, 1.8, 5.3, 4.8], size: 20}
  compare:
    - {role: title,    box: [0.8, 0.5, 11.7, 1.0], size: 28, bold: true}
    - {role: left,     box: [0.8, 1.8, 5.6, 4.8], size: 20}
    - {role: right,    box: [6.9, 1.8, 5.6, 4.8], size: 20}
```
````

- [ ] **Step 6: 寫 mini-deck/STATUS.md**

```markdown
stage: build
title: mini-deck 範例

| # | 資料夾 | script | slides | 備註 |
| 01 | 01_背景 | done | done | |
| 02 | 02_做法 | done | done | 1 張待補圖 |

log:
- 2026-09-07 建立範例資料
```

- [ ] **Step 7: 驗證**

```powershell
Get-ChildItem -Recurse "$env:USERPROFILE\.claude\skills\deck-pipeline\examples\mini-deck" | Select-Object -ExpandProperty FullName
```

Expected: 列出 STATUS.md、SLIDES.md、STYLE.md、01_背景/flow_old.png、02_做法/.gitkeep

---

### Task 2: parse_slides

**Files:**
- Create: `<skill>/scripts/build_pptx.py`
- Create: `<skill>/scripts/tests/test_build_pptx.py`

**Interfaces:**
- Produces:
  - `Page(layout: str, title: str, subtitle: str, bullets: list[str], images: list[tuple[str, str]], table: list[list[str]], notes: str)`
  - `Topic(num: str, name: str, pages: list[Page])`, property `folder -> str` = `f"{num}_{name}"`
  - `Deck(title: str, topics: list[Topic])`, method `pages()` yield `(topic, index_from_1, page)`
  - `parse_slides(text: str) -> Deck`, 格式錯誤丟 `SlidesParseError`
  - 常數 `TODO = "TODO"`

- [ ] **Step 1: 寫失敗測試**

`<skill>/scripts/tests/test_build_pptx.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_pptx as bp  # noqa: E402

SKILL = Path(__file__).resolve().parents[2]
MINI = SKILL / "examples" / "mini-deck"

SLIDES = """# 測試簡報

## 01 背景

### [title] 為什麼
副標一句

### [text] 三個痛點
- 痛點一
- 痛點二

> 講稿對應: 第一段
> 第二行

### [image] 舊流程
![舊流程截圖](01_背景/flow_old.png)
- 一句註解

## 02 做法

### [compare] 舊 vs 新
| 舊 | 新 |
|---|---|
| 手動 | 自動 |

### [image-text] 理想
![描述: 箭頭圖](TODO)
- 六階段
"""


def test_parse_slides_title_and_topics():
    deck = bp.parse_slides(SLIDES)
    assert deck.title == "測試簡報"
    assert [t.folder for t in deck.topics] == ["01_背景", "02_做法"]
    assert [len(t.pages) for t in deck.topics] == [3, 2]


def test_parse_slides_page_fields():
    deck = bp.parse_slides(SLIDES)
    p1, p2, p3 = deck.topics[0].pages
    assert (p1.layout, p1.title, p1.subtitle) == ("title", "為什麼", "副標一句")
    assert p2.bullets == ["痛點一", "痛點二"]
    assert p2.notes == "講稿對應: 第一段\n第二行"
    assert p3.images == [("舊流程截圖", "01_背景/flow_old.png")]
    assert p3.bullets == ["一句註解"]


def test_parse_slides_table_and_todo():
    deck = bp.parse_slides(SLIDES)
    cmp_, img = deck.topics[1].pages
    assert cmp_.table == [["舊", "新"], ["手動", "自動"]]
    assert img.images == [("描述: 箭頭圖", bp.TODO)]


def test_parse_slides_pages_iter():
    deck = bp.parse_slides(SLIDES)
    seq = [(t.num, i, p.layout) for t, i, p in deck.pages()]
    assert seq == [("01", 1, "title"), ("01", 2, "text"), ("01", 3, "image"),
                   ("02", 1, "compare"), ("02", 2, "image-text")]


def test_parse_slides_rejects_page_without_layout():
    with pytest.raises(bp.SlidesParseError, match="版型"):
        bp.parse_slides("# t\n\n## 01 a\n\n### 沒有標記\n")


def test_parse_slides_rejects_missing_title():
    with pytest.raises(bp.SlidesParseError, match="簡報名稱"):
        bp.parse_slides("## 01 a\n\n### [text] x\n")
```

- [ ] **Step 2: 跑測試確認失敗**

```powershell
py -3.12-64 -m pytest "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\tests" -v
```

Expected: 全部 ERROR, `ModuleNotFoundError: No module named 'build_pptx'`

- [ ] **Step 3: 寫 build_pptx.py 的資料模型與 parse_slides**

`<skill>/scripts/build_pptx.py`:

```python
"""deck-pipeline: SLIDES.md + STYLE.md -> 可編輯 pptx

用法:
  py -3.12-64 build_pptx.py <deck資料夾>               # 產 output/<title>.pptx
  py -3.12-64 build_pptx.py <deck資料夾> --images-todo # 只產 IMAGES_TODO.md
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

TODO = "TODO"


class SlidesParseError(ValueError):
    pass


@dataclass
class Page:
    layout: str
    title: str
    subtitle: str = ""
    bullets: list[str] = field(default_factory=list)
    images: list[tuple[str, str]] = field(default_factory=list)  # (描述, 路徑)
    table: list[list[str]] = field(default_factory=list)          # 含表頭列
    notes: str = ""


@dataclass
class Topic:
    num: str
    name: str
    pages: list[Page] = field(default_factory=list)

    @property
    def folder(self) -> str:
        return f"{self.num}_{self.name}"


@dataclass
class Deck:
    title: str
    topics: list[Topic] = field(default_factory=list)

    def pages(self):
        for topic in self.topics:
            for i, page in enumerate(topic.pages, 1):
                yield topic, i, page


RE_TOPIC = re.compile(r"^## (\d+)\s+(.+?)\s*$")
RE_PAGE = re.compile(r"^### \[([\w-]+)\]\s*(.+?)\s*$")
RE_IMAGE = re.compile(r"^!\[(.*?)\]\((.+?)\)\s*$")
RE_TABLE_SEP = re.compile(r"^\|?\s*:?-{2,}")


def parse_slides(text: str) -> Deck:
    deck = Deck(title="")
    topic: Topic | None = None
    page: Page | None = None
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("# "):
            deck.title = line[2:].strip()
            continue
        m = RE_TOPIC.match(line)
        if m:
            topic = Topic(m.group(1), m.group(2))
            deck.topics.append(topic)
            page = None
            continue
        if line.startswith("### "):
            m = RE_PAGE.match(line)
            if not m:
                raise SlidesParseError(f"第{lineno}行: 頁標題缺版型標記, 格式應為 ### [layout] 標題")
            if topic is None:
                raise SlidesParseError(f"第{lineno}行: 頁出現在任何 ## topic 之前")
            page = Page(layout=m.group(1), title=m.group(2))
            topic.pages.append(page)
            continue
        if page is None:
            continue  # topic 標題下、第一頁之前的說明文字忽略
        if line.startswith("> "):
            page.notes = (page.notes + "\n" + line[2:]).strip()
            continue
        if line.startswith("- "):
            page.bullets.append(line[2:].strip())
            continue
        m = RE_IMAGE.match(line)
        if m:
            page.images.append((m.group(1), m.group(2)))
            continue
        if line.startswith("|"):
            if RE_TABLE_SEP.match(line):
                continue
            page.table.append([c.strip() for c in line.strip().strip("|").split("|")])
            continue
        page.subtitle = (page.subtitle + "\n" + line.strip()).strip()
    if not deck.title:
        raise SlidesParseError("缺少 # 簡報名稱")
    return deck
```

- [ ] **Step 4: 跑測試確認通過**

```powershell
py -3.12-64 -m pytest "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\tests" -v
```

Expected: 6 passed

---

### Task 3: parse_style 與 validate

**Files:**
- Modify: `<skill>/scripts/build_pptx.py` (追加)
- Modify: `<skill>/scripts/tests/test_build_pptx.py` (追加)

**Interfaces:**
- Consumes: `Deck`, `Topic.folder`, `Deck.pages()`, `TODO` (Task 2)
- Produces:
  - `Style(slide: dict, theme: dict, layouts: dict)`
  - `parse_style(text: str) -> Style`, 錯誤丟 `StyleParseError`
  - `validate(deck: Deck, style: Style, deck_dir: Path) -> list[str]` 回傳錯誤訊息清單, 空即通過

- [ ] **Step 1: 寫失敗測試** (追加到 test_build_pptx.py 末尾)

````python
STYLE = """# 版型

說明文字, 腳本忽略。

```yaml
slide: {w: 13.333, h: 7.5}
theme:
  bg: "#FFFFFF"
  fg: "#1F2937"
  accent: "#2563EB"
  font_title: "Noto Sans TC"
  font_body: "Noto Sans TC"
layouts:
  title:
    - {role: title, box: [1.0, 2.4, 11.3, 1.4], size: 40, bold: true}
    - {role: subtitle, box: [1.0, 4.0, 11.3, 1.0], size: 22}
  text:
    - {role: title, box: [0.8, 0.6, 11.7, 1.2], size: 32, bold: true}
    - {role: body, box: [0.8, 2.2, 11.7, 4.5], size: 20}
```
"""


def test_parse_style_reads_yaml_block():
    st = bp.parse_style(STYLE)
    assert st.slide == {"w": 13.333, "h": 7.5}
    assert st.theme["accent"] == "#2563EB"
    assert set(st.layouts) == {"title", "text"}
    assert st.layouts["text"][1]["role"] == "body"


def test_parse_style_rejects_missing_yaml():
    with pytest.raises(bp.StyleParseError, match="yaml"):
        bp.parse_style("# 只有文字沒有區塊\n")


def test_parse_style_rejects_missing_key():
    with pytest.raises(bp.StyleParseError, match="layouts"):
        bp.parse_style("```yaml\nslide: {w: 1, h: 1}\ntheme: {}\n```\n")


def test_validate_reports_unknown_layout_and_missing_image(tmp_path):
    deck = bp.parse_slides(SLIDES)   # 用到 image / compare / image-text, STYLE 只定義 title / text
    st = bp.parse_style(STYLE)
    errors = bp.validate(deck, st, tmp_path)
    assert any("01_背景 第3頁 [image]" in e and "版型未在 STYLE.md 定義" in e for e in errors)
    assert any("圖片不存在 01_背景/flow_old.png" in e for e in errors)
    assert not any("TODO" in e for e in errors)   # TODO 不算缺圖


def test_validate_passes_on_mini_deck():
    deck = bp.parse_slides((MINI / "SLIDES.md").read_text(encoding="utf-8"))
    st = bp.parse_style((MINI / "STYLE.md").read_text(encoding="utf-8"))
    assert bp.validate(deck, st, MINI) == []
````

- [ ] **Step 2: 跑測試確認失敗**

```powershell
py -3.12-64 -m pytest "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\tests" -v -k "style or validate"
```

Expected: 5 failed, `AttributeError: module 'build_pptx' has no attribute 'parse_style'`

- [ ] **Step 3: 實作** (追加到 build_pptx.py, 放在 parse_slides 之後)

```python
import yaml  # 放到檔頭 import 區


class StyleParseError(ValueError):
    pass


@dataclass
class Style:
    slide: dict
    theme: dict
    layouts: dict


RE_YAML = re.compile(r"```yaml\s*\n(.*?)\n```", re.S)


def parse_style(text: str) -> Style:
    m = RE_YAML.search(text)
    if not m:
        raise StyleParseError("STYLE.md 找不到 ```yaml 區塊")
    data = yaml.safe_load(m.group(1)) or {}
    for key in ("slide", "theme", "layouts"):
        if key not in data:
            raise StyleParseError(f"STYLE.md yaml 缺少 {key}")
    return Style(data["slide"], data["theme"], data["layouts"])


def validate(deck: Deck, style: Style, deck_dir: Path) -> list[str]:
    errors: list[str] = []
    for topic, i, page in deck.pages():
        where = f"{topic.folder} 第{i}頁 [{page.layout}] {page.title}"
        if page.layout not in style.layouts:
            errors.append(f"{where}: 版型未在 STYLE.md 定義")
        for _desc, path in page.images:
            if path != TODO and not (deck_dir / path).is_file():
                errors.append(f"{where}: 圖片不存在 {path}")
    return errors
```

- [ ] **Step 4: 跑全部測試**

```powershell
py -3.12-64 -m pytest "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\tests" -v
```

Expected: 11 passed

---

### Task 4: render 與 main

**Files:**
- Modify: `<skill>/scripts/build_pptx.py` (追加)
- Modify: `<skill>/scripts/tests/test_build_pptx.py` (追加)

**Interfaces:**
- Consumes: `Deck`, `Style`, `validate`, `TODO`
- Produces:
  - `render(deck: Deck, style: Style, deck_dir: Path) -> pptx.Presentation`
  - `safe_filename(name: str) -> str`
  - `main(argv: list[str] | None = None) -> int` (0 成功, 1 驗證失敗)

- [ ] **Step 1: 寫失敗測試** (追加)

```python
from pptx import Presentation  # 放到檔頭
from pptx.util import Inches   # 放到檔頭


def _build_mini(tmp_path):
    deck = bp.parse_slides((MINI / "SLIDES.md").read_text(encoding="utf-8"))
    st = bp.parse_style((MINI / "STYLE.md").read_text(encoding="utf-8"))
    prs = bp.render(deck, st, MINI)
    out = tmp_path / "mini.pptx"
    prs.save(str(out))
    return Presentation(str(out))


def _texts(slide):
    return [sh.text_frame.text for sh in slide.shapes if sh.has_text_frame]


def test_render_slide_count_and_size(tmp_path):
    prs = _build_mini(tmp_path)
    assert len(prs.slides) == 6
    assert prs.slide_width == Inches(13.333)
    assert prs.slide_height == Inches(7.5)


def test_render_title_and_bullets_are_editable_text(tmp_path):
    prs = _build_mini(tmp_path)
    s1, s2 = prs.slides[0], prs.slides[1]
    assert "為什麼要做這件事" in _texts(s1)
    assert "把散亂素材變成一份簡報" in _texts(s1)
    assert "素材散在各處\n講稿與頁面混在一起\n排版每次從零開始" in _texts(s2)


def test_render_notes(tmp_path):
    prs = _build_mini(tmp_path)
    assert prs.slides[1].notes_slide.notes_text_frame.text == "講稿對應: 背景第一段"
    assert not prs.slides[0].has_notes_slide


def test_render_picture_fits_box(tmp_path):
    prs = _build_mini(tmp_path)
    pics = [sh for sh in prs.slides[2].shapes if sh.shape_type == 13]  # MSO_SHAPE_TYPE.PICTURE
    assert len(pics) == 1
    pic = pics[0]
    # box [0.8, 1.8, 11.7, 4.6], 圖 400x300 → 高度吃滿 4.6, 寬 6.133, 水平置中
    assert abs(pic.height - Inches(4.6)) < Inches(0.01)
    assert abs(pic.width - Inches(4.6 * 400 / 300)) < Inches(0.01)
    assert abs(pic.left - Inches(0.8 + (11.7 - 4.6 * 400 / 300) / 2)) < Inches(0.01)


def test_render_todo_image_becomes_gray_placeholder(tmp_path):
    prs = _build_mini(tmp_path)
    s5 = prs.slides[4]  # 02 第2頁 image-text
    rects = [sh for sh in s5.shapes if sh.shape_type == 1]  # AUTO_SHAPE
    assert len(rects) == 1
    assert rects[0].fill.fore_color.rgb == bp.RGBColor(0xD1, 0xD5, 0xDB)
    assert "[待補圖] 描述: 一張簡化的箭頭圖, 三步變一步" in rects[0].text_frame.text


def test_render_compare_columns(tmp_path):
    prs = _build_mini(tmp_path)
    texts = _texts(prs.slides[5])
    assert "舊\n手動搬檔\n邊寫邊排" in texts
    assert "新\nAI 分類\n先講稿再頁面" in texts


def test_safe_filename():
    assert bp.safe_filename('a/b:c*d?"e<f>g|h') == "a_b_c_d_e_f_g_h"
    assert bp.safe_filename("  ") == "deck"


def test_main_builds_to_output(tmp_path):
    import shutil
    shutil.copytree(MINI, tmp_path / "deck")
    assert bp.main([str(tmp_path / "deck")]) == 0
    assert (tmp_path / "deck" / "output" / "mini-deck 範例.pptx").is_file()


def test_main_returns_1_on_validation_error(tmp_path, capsys):
    import shutil
    shutil.copytree(MINI, tmp_path / "deck")
    (tmp_path / "deck" / "01_背景" / "flow_old.png").unlink()
    assert bp.main([str(tmp_path / "deck")]) == 1
    assert "圖片不存在" in capsys.readouterr().out
    assert not (tmp_path / "deck" / "output").exists()
```

- [ ] **Step 2: 跑測試確認失敗**

```powershell
py -3.12-64 -m pytest "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\tests" -v -k "render or main or safe"
```

Expected: 9 failed, AttributeError 無 render / safe_filename / main

- [ ] **Step 3: 實作** (追加到 build_pptx.py)

檔頭 import 區加入:

```python
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
```

檔尾追加:

```python
PLACEHOLDER_GRAY = RGBColor(0xD1, 0xD5, 0xDB)


def _rgb(hex_str: str) -> RGBColor:
    return RGBColor.from_string(hex_str.lstrip("#"))


def _textbox(slide, box, lines, *, font, size, color, bold=False, first_bold=False):
    x, y, w, h = (Inches(v) for v in box)
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for idx, line in enumerate(lines):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        run = p.add_run()
        run.text = line
        run.font.name = font
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.bold = bold or (first_bold and idx == 0)
    return tb


def _picture_fit(slide, box, img_path: Path):
    x, y, w, h = box
    with Image.open(img_path) as im:
        iw, ih = im.size
    scale = min(w / iw, h / ih)
    pw, ph = iw * scale, ih * scale
    px, py = x + (w - pw) / 2, y + (h - ph) / 2
    slide.shapes.add_picture(str(img_path), Inches(px), Inches(py), Inches(pw), Inches(ph))


def _placeholder(slide, box, desc: str, theme: dict):
    x, y, w, h = (Inches(v) for v in box)
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = PLACEHOLDER_GRAY
    shp.line.fill.background()
    tf = shp.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = f"[待補圖] {desc}"
    run.font.name = theme["font_body"]
    run.font.size = Pt(14)
    run.font.color.rgb = _rgb(theme["fg"])


def _column(page: Page, idx: int) -> list[str]:
    return [row[idx] for row in page.table if len(row) > idx]


def render(deck: Deck, style: Style, deck_dir: Path) -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(style.slide["w"])
    prs.slide_height = Inches(style.slide["h"])
    blank = prs.slide_layouts[6]
    theme = style.theme
    for _topic, _i, page in deck.pages():
        slide = prs.slides.add_slide(blank)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = _rgb(theme["bg"])
        elements = style.layouts[page.layout]
        has_subtitle_el = any(el["role"] == "subtitle" for el in elements)
        img_i = 0
        for el in elements:
            role, box = el["role"], el["box"]
            size = el.get("size", 18)
            bold = el.get("bold", False)
            color = _rgb(el.get("color", theme["fg"]))
            if role == "title":
                _textbox(slide, box, [page.title], font=theme["font_title"], size=size, color=color, bold=bold)
            elif role == "subtitle":
                _textbox(slide, box, page.subtitle.splitlines(), font=theme["font_body"], size=size, color=color, bold=bold)
            elif role == "body":
                lines = page.bullets or ([] if has_subtitle_el else page.subtitle.splitlines())
                _textbox(slide, box, lines, font=theme["font_body"], size=size, color=color, bold=bold)
            elif role == "image":
                if img_i < len(page.images):
                    desc, path = page.images[img_i]
                    img_i += 1
                    if path == TODO:
                        _placeholder(slide, box, desc, theme)
                    else:
                        _picture_fit(slide, box, deck_dir / path)
            elif role in ("left", "right"):
                col = 0 if role == "left" else 1
                _textbox(slide, box, _column(page, col), font=theme["font_body"], size=size, color=color, bold=bold, first_bold=True)
            else:
                raise StyleParseError(f"版型 {page.layout} 有未知 role: {role}")
        if page.notes:
            slide.notes_slide.notes_text_frame.text = page.notes
    return prs


def safe_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "deck"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck_dir", help="工作資料夾, 內含 SLIDES.md 與 STYLE.md")
    ap.add_argument("--images-todo", action="store_true", help="只產 IMAGES_TODO.md, 不 build")
    args = ap.parse_args(argv)
    deck_dir = Path(args.deck_dir).resolve()
    deck = parse_slides((deck_dir / "SLIDES.md").read_text(encoding="utf-8"))
    if args.images_todo:
        (deck_dir / "IMAGES_TODO.md").write_text(images_todo(deck), encoding="utf-8")
        print(f"已寫入 {deck_dir / 'IMAGES_TODO.md'}")
        return 0
    style = parse_style((deck_dir / "STYLE.md").read_text(encoding="utf-8"))
    errors = validate(deck, style, deck_dir)
    if errors:
        print("build 失敗:")
        for e in errors:
            print(" -", e)
        return 1
    prs = render(deck, style, deck_dir)
    out = deck_dir / "output" / f"{safe_filename(deck.title)}.pptx"
    out.parent.mkdir(exist_ok=True)
    prs.save(str(out))
    print(f"已輸出 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

注意 `main` 用到 `images_todo`, 在 Task 5 才實作; Task 4 先放一個暫時版讓 import 不炸:

```python
def images_todo(deck: Deck) -> str:  # Task 5 會替換
    return ""
```

- [ ] **Step 4: 跑全部測試**

```powershell
py -3.12-64 -m pytest "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\tests" -v
```

Expected: 20 passed。若 `test_render_notes` 的 `has_notes_slide` 失敗, 確認 render 只在 `page.notes` 非空時才存取 `notes_slide` (存取即建立)

---

### Task 5: images_todo

**Files:**
- Modify: `<skill>/scripts/build_pptx.py` (替換暫時版)
- Modify: `<skill>/scripts/tests/test_build_pptx.py` (追加)

**Interfaces:**
- Consumes: `Deck.pages()`, `Topic.folder`, `TODO`
- Produces: `images_todo(deck: Deck) -> str` 回傳 IMAGES_TODO.md 全文

- [ ] **Step 1: 寫失敗測試** (追加)

```python
def test_images_todo_lists_only_todo_images():
    deck = bp.parse_slides(SLIDES)
    md = bp.images_todo(deck)
    assert md.startswith("# 待補圖清單")
    assert "| 02_做法 第2頁 理想 | 描述: 箭頭圖 | 02_做法/p02_img1.png |" in md
    assert "flow_old" not in md


def test_images_todo_empty():
    deck = bp.parse_slides("# t\n\n## 01 a\n\n### [text] x\n- y\n")
    assert "| (無) | | |" in bp.images_todo(deck)


def test_main_images_todo_flag(tmp_path):
    import shutil
    shutil.copytree(MINI, tmp_path / "deck")
    assert bp.main([str(tmp_path / "deck"), "--images-todo"]) == 0
    md = (tmp_path / "deck" / "IMAGES_TODO.md").read_text(encoding="utf-8")
    assert "02_做法/p02_img1.png" in md
    assert not (tmp_path / "deck" / "output").exists()
```

- [ ] **Step 2: 跑測試確認失敗**

```powershell
py -3.12-64 -m pytest "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\tests" -v -k images_todo
```

Expected: 3 failed (暫時版回傳空字串)

- [ ] **Step 3: 替換實作**

```python
def images_todo(deck: Deck) -> str:
    rows = [
        "# 待補圖清單",
        "",
        "由 SLIDES.md 中路徑為 TODO 的圖片產生。補圖後把 SLIDES.md 的 TODO 換成實際路徑, 重跑 `--images-todo` 更新本檔。",
        "",
        "| 頁 | 描述 | 建議檔名 |",
        "|---|---|---|",
    ]
    count = 0
    for topic, i, page in deck.pages():
        for k, (desc, path) in enumerate(page.images, 1):
            if path == TODO:
                count += 1
                rows.append(f"| {topic.folder} 第{i}頁 {page.title} | {desc} | {topic.folder}/p{i:02d}_img{k}.png |")
    if count == 0:
        rows.append("| (無) | | |")
    return "\n".join(rows) + "\n"
```

- [ ] **Step 4: 跑全部測試**

```powershell
py -3.12-64 -m pytest "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\tests" -v
```

Expected: 23 passed

- [ ] **Step 5: 對 mini-deck 實跑一次**

```powershell
$m = "$env:USERPROFILE\.claude\skills\deck-pipeline\examples\mini-deck"
py -3.12-64 "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\build_pptx.py" $m --images-todo
py -3.12-64 "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\build_pptx.py" $m
```

Expected: 印出「已寫入 ...IMAGES_TODO.md」與「已輸出 ...output\mini-deck 範例.pptx」。這兩個產出留在 examples 裡當範例

---

### Task 6: references/formats.md

**Files:**
- Create: `<skill>/references/formats.md`

**Interfaces:**
- Consumes: Task 2~5 定案的 parse 規則 (這份文件是那些規則的人讀版, 兩邊必須一致)

- [ ] **Step 1: 寫檔**

````markdown
# deck-pipeline 檔案格式

四個檔案都放在工作資料夾根目錄。腳本只讀 SLIDES.md 與 STYLE.md; STATUS.md 與 IMAGES_TODO.md 是給人與 AI 對話用的。

## STATUS.md

```
stage: slides            // collect | organize | script | slides | style | build
title: <簡報名稱>

| # | 資料夾 | script | slides | 備註 |
| 01 | 01_背景 | done | doing | +素材 2026-09-07 note_xxx.md |
| 02 | 02_做法 | done | - | |

log:
- 2026-09-07 organize 定案, 6 份素材, 1 份拆分
```

- `stage`: 目前所在階段, 六選一
- topic 表: 一行一個 topic, `#` 兩位數與資料夾前綴一致
- `script` / `slides` 欄位值: `-` 未開始 / `doing` / `done` / `stale` (前面階段被回頭改過, 這欄要重看)
- 備註: 新增素材記 `+素材 <日期> <檔名>`; 其他事件自由寫
- log: 一行一事件, 日期開頭, 新的加在最下面
- 只記進度與事件, 不放內容

## SLIDES.md

```
# <簡報名稱>

## 01 背景

### [title] 為什麼要做這件事
副標一句

### [text] 現況三個痛點
- 痛點一
- 痛點二

### [image] 理想的樣子
![描述: 一張簡化的箭頭圖, 三步變一步](TODO)
- 一句註解

### [compare] 舊 vs 新
| 舊 | 新 |
| 手動 | 自動 |

> 講稿對應: 第一段
```

結構規則:
- `# ` 簡報名稱, 只有一個, 缺少會報錯; 同時決定輸出檔名 `output/<簡報名稱>.pptx`
- `## <兩位數> <topic名>` 一個 topic, 必須跟資料夾 `<兩位數>_<topic名>` 對得起來
- `### [<版型>] <頁標題>` 一頁; 缺方括號會報錯
- 不用 `---` 分頁

頁內元素 (寫在 `###` 之後, 到下一個 `###` 或 `##` 為止):
- `- ` 開頭 → 條列, 對應 role `body`
- `![描述](路徑)` → 圖片, 對應 role `image`; 路徑相對於工作資料夾; 路徑填 `TODO` 即待補圖, 描述要寫清楚讓人能找圖或生圖
- `| a | b |` 表格列 → 對應 role `left` / `right`, 第一列是欄標題 (會加粗); `|---|` 分隔列可有可無
- `> ` 開頭 → speaker notes, 多行會合併
- 其他純文字行 → 對應 role `subtitle`; 若版型沒有 `subtitle` 元素但有 `body` 且沒有條列, 會補進 `body`

版型初始字彙與慣用元素:

| 版型 | 用途 | 通常含的 role |
|---|---|---|
| `title` | 全簡報開頭 | title, subtitle |
| `section` | 章節分隔 | title |
| `text` | 純文字重點 | title, body |
| `image` | 一張圖為主 | title, image, body (底部一行) |
| `image-text` | 左圖右文 | title, image, body |
| `compare` | 兩欄對比 | title, left, right |

版型可以新增, 只要 STYLE.md 有定義。

## IMAGES_TODO.md

由 `build_pptx.py <deck> --images-todo` 產生, 不手寫。

```
| 頁 | 描述 | 建議檔名 |
|---|---|---|
| 02_做法 第2頁 理想的樣子 | 描述: 一張簡化的箭頭圖 | 02_做法/p02_img1.png |
```

補圖流程: 圖放進建議路徑 → SLIDES.md 該行 `TODO` 改成路徑 → 重跑 `--images-todo` → 清單消掉那一筆。

## STYLE.md

上半自由文字, 給人讀 (配色意圖、字體選擇、每種版型長什麼樣、canvas 定案的 artboard 名稱)。腳本忽略。

下半一個 ```` ```yaml ```` 區塊, 腳本只讀這裡:

```yaml
slide: {w: 13.333, h: 7.5}       # 16:9 英吋
theme:
  bg: "#FFFFFF"                  # 背景
  fg: "#1F2937"                  # 預設文字色
  accent: "#2563EB"              # 強調色, 元素可用 color 覆寫
  font_title: "Noto Sans TC"
  font_body: "Noto Sans TC"
layouts:
  text:
    - {role: title, box: [0.8, 0.6, 11.7, 1.2], size: 32, bold: true}
    - {role: body,  box: [0.8, 2.2, 11.7, 4.5], size: 20}
  image:
    - {role: title, box: [0.8, 0.5, 11.7, 1.0], size: 28, bold: true}
    - {role: image, box: [0.8, 1.8, 11.7, 4.6]}
    - {role: body,  box: [0.8, 6.6, 11.7, 0.6], size: 16}
```

- `slide` / `theme` / `layouts` 三個 key 缺一報錯
- 每個版型 = 元素清單, 依序放置
- 元素欄位: `role` (必填) / `box` [x, y, w, h] 英吋 (必填) / `size` pt (文字類, 預設 18) / `bold` (預設 false) / `color` hex (預設 theme.fg)
- role 字彙: `title` `subtitle` `body` `image` `left` `right`; 其他值報錯
- 同一版型可放多個 `image` 元素, 依序吃該頁的第 1、2、... 張圖; 頁的圖比元素多的忽略, 比元素少的元素留空
- 圖片等比縮放置中放進 box; TODO 圖畫灰底 (#D1D5DB) 矩形加描述
- 從 canvas 轉寫尺寸: canvas artboard 1280x720 px 時, 英吋 = px / 96
````

- [ ] **Step 2: 驗證與腳本一致**

逐條核對 formats.md 中「規則」段落與 `build_pptx.py` 的 `parse_slides` / `parse_style` / `render` 行為: `###` 缺方括號報錯、`TODO` 不算缺圖、表格第一列加粗、subtitle 補進 body 的條件、role 未知報錯。有出入以腳本為準改文件。

---

### Task 7: references/stage-style.md

**Files:**
- Create: `<skill>/references/stage-style.md`

**Interfaces:**
- Consumes: STYLE.md 格式 (Task 6), `design` skill

- [ ] **Step 1: 寫檔**

````markdown
# 階段 5: 版型定案

目標: 從 SLIDES.md 歸納出要幾種版型, 用 design skill 出方案讓使用者挑, 把定案轉寫成 STYLE.md。
版型定一次整份沿用, 不逐頁調。

## 1. 歸納版型集合

掃 SLIDES.md 所有 `### [xxx]`, 列出用到的版型與頁數:

```
title 1 頁 / section 3 頁 / text 8 頁 / image 5 頁 / image-text 2 頁 / compare 1 頁
```

只出有用到的版型。同時從每種版型挑一頁真實內容當 artboard 的填充文字 (不要用 lorem ipsum, 使用者要看得出實際長度合不合)。

## 2. 問使用者風格方向

一個問題, 純文字: 有沒有既定的配色/字體/品牌要求, 或參考的簡報風格。沒有就用預設 (白底深灰字單一強調色, Noto Sans TC)。

## 3. 呼叫 design skill

一個 canvas, 每種版型 2~3 個 artboard 方案。呼叫 `Skill design` 時 prompt 要包含:

- artboard 尺寸 1280x720 (16:9, 之後 px/96 直接換算英吋)
- artboard 命名 `<版型>-A` `<版型>-B` `<版型>-C`, 依版型分排擺放
- 每個 artboard 的填充內容用第 1 步挑的真實頁面文字與圖 (圖用灰色佔位塊, 標上 SLIDES.md 的描述)
- 同一 canvas 內所有方案共用同一組配色與字體 (第 2 步結果), 差異在版面配置
- 每個元素明確對應一個 role (title / subtitle / body / image / left / right), 元素不要多於 role 需要的數量; 裝飾性線條色塊可以有, 但要能用 theme 的 bg/accent 表達

## 4. 使用者挑選與微調

使用者在 canvas 上挑每種版型的方案並微調。結束後請使用者告知每種版型選了哪個 artboard。

## 5. 轉寫 STYLE.md

用 `Artifact read` 讀回 canvas, 找到被選的 artboard, 對每個元素:

- 位置尺寸 px → 英吋: 除以 96, 取到小數第二位
- 字級 px → pt: 乘 0.75, 取整
- 顏色取 hex; 跟 theme.fg 相同就不寫 `color`, 不同 (通常是強調色) 才寫
- 字重 ≥ 600 視為 bold

寫入 STYLE.md:
- 上半: 配色與字體說明、每種版型一句話描述、記下選用的 artboard 名稱與 canvas URL
- 下半: yaml, 格式見 `formats.md`

寫完跑一次 `build_pptx.py <deck>` 確認能產出, 請使用者開 pptx 看跟 canvas 是否對得上。像素級差異是預期的, 只複刻規則。

## 6. design skill 不可用時

退化為文字描述: 每種版型給 2~3 個文字版面方案 (各元素位置以英吋描述), 使用者挑, 直接寫 STYLE.md。

## 完成條件

STYLE.md 存在, yaml 涵蓋 SLIDES.md 用到的全部版型, 使用者確認。STATUS.md 的 stage 改為 build。
````

- [ ] **Step 2: 驗證**

確認文中每個 role 名稱、STYLE.md 欄位名稱與 formats.md 一致; 確認 1280x720 / 96 = 13.333x7.5 與 Global Constraints 一致。

---

### Task 8: SKILL.md

**Files:**
- Create: `<skill>/SKILL.md`

**Interfaces:**
- Consumes: `references/formats.md`, `references/stage-style.md`, `scripts/build_pptx.py` CLI

- [ ] **Step 1: 寫檔**

````markdown
---
name: deck-pipeline
description: 觸發詞「做簡報」或 /deck-pipeline <資料夾路徑>。把一個堆滿簡報素材 (截圖、txt、md) 的資料夾, 經六個階段 (堆素材 → 分 topic → 講稿 → 頁面內容 → 版型定案 → 生 pptx) 帶到可編輯 pptx。跨多次會話進行, 進度靠資料夾內 STATUS.md 銜接。使用者提到要做簡報、整理簡報素材、寫講稿、把講稿變投影片、或指向一個已有 STATUS.md 的資料夾時使用。
---

# deck-pipeline

一個資料夾, 六個階段, 每一步都是使用者拍板、AI 動手。輸入輸出都在同一個資料夾原地演化, 與任何專案無關。

格式規格在 `references/formats.md`, 階段 5 細節在 `references/stage-style.md`, 需要時才讀。

## 每次呼叫的固定開場

1. 拿到資料夾路徑 (參數沒帶就問)。資料夾不存在就停下來問
2. 讀 `STATUS.md`。不存在 → 視為 collect 起點, 建立它。格式損壞 → 回報, 問使用者重建還是手修, 不自行猜
3. 比對 stage 與資料夾實況 (例如 stage: organize 但根目錄已有 SLIDES.md)。有打架 → 回報差異, 以使用者裁決為準更新 STATUS.md
4. 回報一句: 「目前在 X 階段, Y 個 topic, 其中 Z 個講稿完成」
5. 問: 繼續當前階段, 還是回頭改前面的東西

## 互動原則

- 全部純文字對話, 不用 AskUserQuestion 選單
- 逐 topic 確認, 不一次產完整份再問
- 提案先給結論與理由, 使用者拍板才動檔案
- 所有素材必須是資料夾裡的檔案, 不存在「只在對話裡講過」的素材 (見「素材規則」)

## 資料夾樣貌

```
<deck>/
  STATUS.md            進度與 topic 表
  (散檔)               階段 1 堆放區
  01_<topic>/          階段 2 後: 素材搬進來, 前綴即順序
  _unsorted/           決定不用的素材, 不刪
  _archive/            被拆分過的原始檔, 不刪
  SCRIPT.md            講稿, 單一檔
  SLIDES.md            頁面內容, 單一檔
  IMAGES_TODO.md       待補圖清單 (腳本產生)
  STYLE.md             版型規則
  output/<title>.pptx
```

## 六階段

### 1. collect 堆素材

- 做: 建立 STATUS.md (`stage: collect`)。素材由使用者自行堆放, AI 不動
- 完成: 使用者說堆好了 → stage 改 organize

### 2. organize 分 topic

- 讀全部散檔: 截圖用 Read 看圖, 文字檔讀內容。檔案多就用 subagent 平行讀回摘要
- 提出 topic 切分與順序, 附每份素材的歸屬建議, 標出需要拆分的檔
- 使用者反覆調整到滿意才動檔
- 定案後: 建 `01_<topic>/` 子資料夾、搬檔 (不複製)、拆分 (見素材規則)、不用的進 `_unsorted/`、寫 STATUS.md topic 表
- 完成: 根目錄除 STATUS.md 外沒有散檔; `_archive/` 每個檔都對得到至少一個拆分檔 → stage 改 script

### 3. script 講稿

- 逐 topic 寫 `SCRIPT.md`, 每個 topic 一個 `## 01 <topic>` 章節
- 內容是要「講」的東西: 長文、敘述、鋪陳、可帶「這邊放 xxx.png」註記。不是要放上投影片的字
- 每個 topic 寫完停下給使用者看, 回饋修改後才往下一個; STATUS.md 該 topic `script` 欄 doing → done
- 完成: 全部 topic `script: done` → stage 改 slides

### 4. slides 頁面內容

- 從 SCRIPT.md 出發, 逐 topic 擬頁面寫進 `SLIDES.md`, 格式見 `references/formats.md`
- 每頁只留最核心的字, 能用圖就用圖。有現成截圖就填路徑, 沒有就寫圖片描述、路徑填 `TODO`, 描述要具體到能拿去找圖或生圖
- 用 `> ` 註記對應講稿段落, 會進 speaker notes
- 逐 topic 確認; STATUS.md 該 topic `slides` 欄 doing → done
- 全部完成後跑 `py -3.12-64 <skill>/scripts/build_pptx.py <deck> --images-todo` 產 IMAGES_TODO.md, 告知使用者哪些圖要補。補圖不在 skill 範圍, 沒補的圖 build 時會是灰框
- 完成: 全部 topic `slides: done` → stage 改 style

### 5. style 版型定案

照 `references/stage-style.md` 做。摘要: 歸納 SLIDES.md 用到的版型 → 問風格方向 → design skill 出 canvas (每版型 2~3 方案) → 使用者挑選微調 → 轉寫 STYLE.md → 使用者確認 → stage 改 build。

### 6. build 生 pptx

```
py -3.12-64 <skill>/scripts/build_pptx.py <deck>
```

- 成功: `output/<title>.pptx`, 文字皆可編輯, TODO 圖為灰框加描述, `>` 進 notes
- 失敗: 腳本列出全部錯誤 (版型未定義 / 圖片不存在), 修 SLIDES.md 或 STYLE.md 後重跑
- 改了 SLIDES.md 或 STYLE.md 就重 build, 每次整份重建
- 相依: `py -3.12-64 -m pip install python-pptx pyyaml`

## 素材規則 (所有階段適用)

任何時候新增素材都走同一套: 落檔 → 歸 topic → STATUS.md 該 topic 備註記 `+素材 <日期> <檔名>`。還沒有 topic 就放根目錄等分類。

- **使用者請 AI 收集**: WebSearch / WebFetch 找, 每份內容一個 md 檔, 檔頭記來源 URL 與抓取日期。網路圖片用 PowerShell 下載成檔案, 來源 URL 記進 STATUS.md log
- **對話補述**: 使用者在對話裡講的補充, 當場寫成 `note_<主題關鍵字>.md`
- **拆分**: 一份文字檔內文跨多個 topic 時, 拆成 `<原檔名>__<topic關鍵字>.md`, 每個拆分檔檔頭記「拆自: <原檔名>, 第 X~Y 段」; 原檔搬進 `_archive/` 不刪

## 回頭修改

允許回到任何前面階段。改動後, 在 STATUS.md 對應 topic 的後續階段欄位標 `stale`, 提醒要重看。stale 不阻擋 build。

## 錯誤處理

- STATUS.md 損壞: 問使用者, 不自行重建
- stage 與資料夾實況打架: 回報, 使用者裁決
- design skill 不可用: 階段 5 退化為文字描述方案 (見 stage-style.md 第 6 節)
- build 失敗: 一次列全部錯誤, 不逐個中斷
````

- [ ] **Step 2: 驗證 frontmatter 與路徑**

```powershell
Get-Content "$env:USERPROFILE\.claude\skills\deck-pipeline\SKILL.md" -TotalCount 4
Test-Path "$env:USERPROFILE\.claude\skills\deck-pipeline\references\formats.md", "$env:USERPROFILE\.claude\skills\deck-pipeline\references\stage-style.md", "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\build_pptx.py"
```

Expected: frontmatter 三行完整; 三個 True

---

### Task 9: 端到端 smoke test

**Files:**
- 無新增; 驗證 Task 1~8 整體

- [ ] **Step 1: 全部測試**

```powershell
py -3.12-64 -m pytest "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\tests" -v
```

Expected: 23 passed

- [ ] **Step 2: 重 build mini-deck 並開檔**

```powershell
$m = "$env:USERPROFILE\.claude\skills\deck-pipeline\examples\mini-deck"
py -3.12-64 "$env:USERPROFILE\.claude\skills\deck-pipeline\scripts\build_pptx.py" $m
Start-Process "$m\output\mini-deck 範例.pptx"
```

換手給使用者確認: 6 頁; 第 1 頁標題與副標可點選編輯; 第 3 頁有藍色圖片置中; 第 5 頁左邊是灰框寫「[待補圖] ...」; 第 6 頁左右兩欄第一行加粗; 第 2 頁備忘稿有「講稿對應: 背景第一段」

- [ ] **Step 3: 新 session 觸發測試**

開新 Claude Code session, 輸入「做簡報」或 `/deck-pipeline <mini-deck 路徑>`。
Expected: skill 被載入, 開場回報「目前在 build 階段, 2 個 topic, 其中 2 個講稿完成」, 並問要繼續還是回頭改

- [ ] **Step 4: 回頭修改路徑測試**

在同一 session 說「我想把兩個 topic 順序換過來」。
Expected: AI 提案改資料夾名與 SLIDES.md / SCRIPT.md 章節編號, 使用者同意後執行, STATUS.md 兩個 topic 的 `slides` 欄標 `stale`, 提醒重看
