"""build_dc_html: SLIDES.md + STYLE.md -> deck-stage .dc.html"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_dc_html import PX_PER_INCH, PX_PER_PT, main, render, upload_manifest  # noqa: E402
from build_pptx import parse_slides, parse_style  # noqa: E402

STYLE = """
```yaml
slide: {w: 13.333, h: 7.5}
theme:
  bg: "#FAF7F2"
  fg: "#2B2622"
  accent: "#B45309"
  font_title: "Noto Serif TC"
  font_body: "Noto Sans TC"
layouts:
  title:
    - {role: title, box: [1.0, 2.0, 11.0, 1.0], size: 44, bold: true}
    - {role: subtitle, box: [1.0, 3.5, 11.0, 0.5], size: 16}
  image-text:
    - {role: title, box: [0.5, 0.5, 12.0, 0.6], size: 27, bold: true}
    - {role: image, box: [0.5, 1.5, 6.0, 4.5]}
    - {role: body, box: [7.0, 1.5, 5.5, 4.5], size: 18}
  table:
    - {role: title, box: [0.5, 0.5, 12.0, 0.6], size: 27, bold: true}
    - {role: table, box: [0.5, 1.5, 12.0, 3.0], size: 18, header_bg: "#2B2622", header_fg: "#FAF7F2"}
    - {role: body, box: [0.5, 5.0, 12.0, 0.6], size: 18, color: "#B45309"}
```
"""

SLIDES = """# 測試簡報

## 01 主題

### [title] 測試簡報
副標 & 說明

### [image-text] 左圖右文
![示意圖](01_主題/圖 (1).svg)
- 第一點
- 第二點 <b>

> 講稿一
> 講稿二

### [table] 表格頁
| 項目 | 數值 |
| A | 1 |
| B | 2 |
- 小結
"""


@pytest.fixture
def deck_dir(tmp_path: Path) -> Path:
    (tmp_path / "SLIDES.md").write_text(SLIDES, encoding="utf-8")
    (tmp_path / "STYLE.md").write_text(STYLE, encoding="utf-8")
    (tmp_path / "01_主題").mkdir()
    (tmp_path / "01_主題" / "圖 (1).svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>', encoding="utf-8"
    )
    return tmp_path


def _render(deck_dir: Path) -> str:
    deck = parse_slides((deck_dir / "SLIDES.md").read_text(encoding="utf-8"))
    style = parse_style((deck_dir / "STYLE.md").read_text(encoding="utf-8"))
    return render(deck, style, deck_dir)


def test_每頁一個section_且帶頁碼與speaker_notes(deck_dir):
    html = _render(deck_dir)
    assert html.count("<section ") == 3
    assert 'data-screen-label="02"' in html
    assert 'data-speaker-notes="講稿一 講稿二"' in html
    assert 'component-from-global-scope="deck-stage"' in html


def test_座標與字級換算_英吋x144_pt_x2(deck_dir):
    html = _render(deck_dir)
    # title box [1.0, 2.0, 11.0, 1.0] -> left 144 top 288 width 1584 height 144
    assert f"left:{1 * PX_PER_INCH}px;top:{2 * PX_PER_INCH}px;width:{round(11 * PX_PER_INCH)}px;height:{PX_PER_INCH}px" in html
    assert f"font-size:{44 * PX_PER_PT}px;font-weight:700" in html


def test_圖片路徑做URL編碼_文字做HTML跳脫(deck_dir):
    html = _render(deck_dir)
    assert 'src="01_%E4%B8%BB%E9%A1%8C/%E5%9C%96%20%281%29.svg"' in html
    assert "副標 &amp; 說明" in html
    assert "第二點 &lt;b&gt;" in html


def test_table_role_輸出真表格_表頭套header色(deck_dir):
    html = _render(deck_dir)
    assert "<table " in html
    assert '<th style="background:#2B2622;color:#FAF7F2;' in html
    assert html.count("<tr>") == 3


def test_table後接body時_兩者放同一個flow容器_不用body絕對座標(deck_dir):
    html = _render(deck_dir)
    # table box [0.5, 1.5, 12.0, 3.0], body box [0.5, 5.0, 12.0, 0.6] -> 容器 top 216, 高 (5.6-1.5)*144=590, gap (5.0-4.5)*144=72
    assert "left:72px;top:216px;width:1728px;height:590px;display:flex;flex-direction:column;gap:72px;" in html
    assert f"top:{round(5.0 * PX_PER_INCH)}px" not in html


def test_圖片依實際尺寸等比縮放置中_寫死width_height(deck_dir):
    html = _render(deck_dir)
    # svg viewBox 10x10, box [0.5, 1.5, 6.0, 4.5] -> 648x648, 水平置中 left 72+(864-648)/2=180, top 216
    assert 'style="position:absolute;left:180px;top:216px;width:648px;height:648px;"' in html


def test_upload_manifest_分文字與二進位(deck_dir):
    deck = parse_slides((deck_dir / "SLIDES.md").read_text(encoding="utf-8"))
    m = upload_manifest(deck, deck_dir)
    assert [f["path"] for f in m["text"]] == ["01_主題/圖 (1).svg"]
    assert m["binary"] == []


def test_main_產出dc_html與upload_json(deck_dir):
    assert main([str(deck_dir)]) == 0
    assert (deck_dir / "output" / "測試簡報.dc.html").is_file()
    assert (deck_dir / "output" / "測試簡報.upload.json").is_file()


def test_圖片不存在時失敗並列錯誤(deck_dir, capsys):
    (deck_dir / "01_主題" / "圖 (1).svg").unlink()
    assert main([str(deck_dir)]) == 1
    assert "圖片不存在" in capsys.readouterr().out
