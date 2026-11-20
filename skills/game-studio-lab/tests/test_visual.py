"""視覺設計: 元素清單 / 挑選結果解析、方案頁、視覺方向。"""
import pytest

from lab.visual import build_visual_page, missing_options, parse_elements, parse_visual_pick, write_direction

ELEMENTS = """底版: deepen-2/game-b

## title — 開始畫面
類型: 動態
內容: 以主視覺呈現的小動畫
為什麼是核心: 玩家第一眼看到的畫面

## hero — 主角
類型：靜態
內容: 主角造型
為什麼是核心: 整場都看著它
"""


def test_parse_elements_ok():
    got = parse_elements(ELEMENTS)
    assert got["base"] == "deepen-2/game-b"
    assert [e["code"] for e in got["elements"]] == ["title", "hero"]
    assert got["elements"][0] == {"code": "title", "name": "開始畫面", "kind": "anim",
                                  "content": "以主視覺呈現的小動畫", "why": "玩家第一眼看到的畫面"}
    assert got["elements"][1]["kind"] == "static"


@pytest.mark.parametrize("text,word", [
    (ELEMENTS.replace("底版: deepen-2/game-b\n", ""), "底版"),
    ("底版: deepen-1/game-a\n", "元素"),
    (ELEMENTS.replace("類型: 動態\n", ""), "title"),
    (ELEMENTS.replace("## title", "## Title"), "Title"),
    (ELEMENTS.replace("類型: 動態", "類型: 會動"), "會動"),
])
def test_parse_elements_rejects(text, word):
    with pytest.raises(ValueError, match=word):
        parse_elements(text)


def test_parse_pick_ok():
    got = parse_visual_pick("title: b\nhero：A，再胖一點\n", ["title", "hero"])
    assert got == {"title": {"id": "B", "note": ""}, "hero": {"id": "A", "note": "再胖一點"}}


@pytest.mark.parametrize("text,word", [
    ("title: A\n", "hero"),
    ("title: D\nhero: A\n", "D"),
    ("title: A\nhero: A\nboss: B\n", "boss"),
])
def test_parse_pick_rejects(text, word):
    with pytest.raises(ValueError, match=word):
        parse_visual_pick(text, ["title", "hero"])


def test_parse_pick_redo_subset():
    got = parse_visual_pick("hero: 都太細, 要更粗獷\n", ["title", "hero"], redo=True)
    assert got == {"hero": {"id": "", "note": "都太細, 要更粗獷"}}
    with pytest.raises(ValueError):
        parse_visual_pick("\n", ["title", "hero"], redo=True)


def write_options(vdir, codes=("title", "hero")):
    opts = vdir / "options"
    opts.mkdir(parents=True, exist_ok=True)
    for c in codes:
        for i in "ABC":
            (opts / f"{c}-{i}.js").write_text(
                f"window.VISUAL_OPTION={{element:'{c}',id:'{i}',kind:'anim',size:[320,180],duration:2,loop:true,"
                f"draw(ctx,t){{ctx.fillRect(0,0,10,10)/*{c}{i}*/}}}};", encoding="utf-8")
        (opts / f"{c}.md").write_text(f"A: {c} 方向一\nB: {c} 方向二\nC: {c} 方向三\n", encoding="utf-8")


def test_missing_options(tmp_path):
    vdir = tmp_path / "visual"
    write_options(vdir, ["title"])
    assert missing_options(vdir / "options", ["title", "hero"]) == [
        "hero-A.js", "hero-B.js", "hero-C.js", "hero.md"]


def test_build_page(tmp_path):
    vdir = tmp_path / "visual"
    write_options(vdir)
    art = tmp_path / "art.js"
    art.write_text("window.Art={marker:'ART_MARKER'};", encoding="utf-8")
    page = build_visual_page(vdir, parse_elements(ELEMENTS)["elements"], art)
    text = page.read_text(encoding="utf-8")
    assert page == vdir / "options" / "index.html"
    assert "ART_MARKER" in text and "/*titleB*/" in text and "/*heroC*/" in text
    assert "開始畫面" in text and "title 方向二" in text and "播放" in text
    assert "try" in text and "catch" in text


def test_write_direction(tmp_path):
    vdir = tmp_path / "visual"
    write_options(vdir)
    parsed = parse_elements(ELEMENTS)
    out = write_direction(vdir, parsed, {"title": {"id": "B", "note": ""}, "hero": {"id": "A", "note": "再胖一點"}})
    text = out.read_text(encoding="utf-8")
    assert out == vdir / "direction.md"
    assert "deepen-2/game-b" in text
    assert "options/title-B.js" in text and "title 方向二" in text
    assert "options/hero-A.js" in text and "再胖一點" in text
