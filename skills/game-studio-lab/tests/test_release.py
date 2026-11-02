"""發布階段: 使用者檔解析、PNG、選擇頁、素材資訊, 以及發布子圖的走向。"""
import json
import shutil
import sqlite3
from pathlib import Path

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from lab.checker import NodeChecker
from lab.fake import FakeRunner
from lab.graph import Deps, LabError
from lab.loader import add_loader
from lab.release_graph import build_release_graph
from lab.renderer import ChromeRenderer, FakeRenderer, find_chrome
from lab.release import (aspect_ratio, build_options_page, parse_release_info, parse_release_pick, site_rule_warnings,
                         png_size, write_asset_info, write_png, prune_release_game,
                         write_site_info, touch_mode)

INFO = {"name": "幽影接力", "code": "ghost-echo", "intro": "和過去的自己接力闖關。", "time": "5–10 分鐘",
        "time_estimated": True, "ratio": "9:16", "ratio_site": False}
COLORS = [{"id": "1", "bg": "#f29cac", "fg": "#2d2144", "note": "粉"},
          {"id": "2", "bg": "#4776c3", "fg": "#ffffff", "note": "藍"},
          {"id": "3", "bg": "#e0c64f", "fg": "#2d2144", "note": "金"}]


def test_parse_release_info_ok():
    got = parse_release_info("名稱: 幽影接力\n代號：ghost-echo\n介紹: 和過去的自己接力闖關。\n")
    assert got == {"name": "幽影接力", "code": "ghost-echo", "intro": "和過去的自己接力闖關。"}


@pytest.mark.parametrize("text,word", [
    ("名稱: 幽影接力\n代號: ghost-echo\n", "介紹"),
    ("名稱: 幽影接力\n代號: Ghost_Echo\n介紹: x\n", "代號"),
])
def test_parse_release_info_rejects(text, word):
    with pytest.raises(ValueError, match=word):
        parse_release_info(text)


def test_parse_release_pick():
    assert parse_release_pick("圖示: b\n主色: 2\n橫幅: A") == {"icon": "B", "color": "2", "banner": "A"}
    with pytest.raises(ValueError, match="主色"):
        parse_release_pick("圖示: B\n主色: 4\n橫幅: A")


@pytest.mark.parametrize("canvas,want", [({"width": 1280, "height": 720, "maxWidth": 1680}, ("16:9", True, "16:9-21:9")),
                                         ({"width": 1280, "height": 720}, ("16:9", True, "16:9")),
                                         ({"width": 1680, "height": 720}, ("21:9", False, "21:9")),
                                         ({"width": 720, "height": 1280}, ("9:16", False, "9:16")),
                                         ({"width": 480, "height": 640}, ("3:4", False, "3:4"))])
def test_aspect_ratio(canvas, want):
    assert aspect_ratio({"canvas": canvas}) == want
    assert aspect_ratio({}) == ("未知", False, "未知")


def test_png_roundtrip(tmp_path):
    write_png(tmp_path / "a.png", 512, 512)
    assert png_size(tmp_path / "a.png") == (512, 512)


def test_options_page_lists_all(tmp_path):
    (tmp_path / "options").mkdir()
    page = build_options_page(tmp_path, INFO, COLORS).read_text(encoding="utf-8")
    for s in ["圖示 A", "圖示 B", "圖示 C", "主色 1", "主色 2", "主色 3", "橫幅 A", "橫幅 C",
              "#f29cac", "#4776c3", "#e0c64f", "icon-a.png", "banner-c.png", "pattern-3.png", "幽影接力"]:
        assert s in page
    assert "<button" not in page and "<input" not in page


def test_asset_info_fields(tmp_path):
    text = write_asset_info(tmp_path, INFO, COLORS[1]).read_text(encoding="utf-8")
    for s in ["遊戲代號", "遊戲名稱", "遊戲介紹", "遊玩時長", "遊戲主色", "遊戲畫面比例",
              "ghost-echo", "5–10 分鐘(估計)", "#4776c3", "#ffffff", "白色字",
              "不是 16:9"]:
        assert s in text
    assert "操作方式說明" not in text


def test_site_info_matches_website_format(tmp_path):
    info = {**INFO, "time": "5-10 分鐘", "ratio": "16:9", "mobile_ratio": "16:9-21:9"}
    data = json.loads(write_site_info(tmp_path, info, {"bg": "#4AC", "fg": "#FFF"}).read_text(encoding="utf-8"))
    assert data == {"code": "ghost-echo", "name": "幽影接力", "intro": "和過去的自己接力闖關。", "time": "5–10 分鐘",
                    "color": "#44aacc", "textColor": "#ffffff", "ratio": "16:9",
                    "mobileRatio": "16:9-21:9"}
    data = json.loads(write_site_info(tmp_path, INFO, COLORS[0]).read_text(encoding="utf-8"))
    assert data["textColor"] == "#2d2144" and data["mobileRatio"] == "9:16" and "mobile" not in data and "device" not in data


def test_prune_release_game_keeps_only_runtime_files(tmp_path):
    g = tmp_path / "game"
    for f, body in {"index.html": '<script src="art/art.js"></script><script src="game.js"></script>',
                    "game.js": "Snd.load('audio/sound.js')", "art/art.js": "", "art/style.md": "",
                    "art/ref-objects.js": "", "audio/sound.js": "", "audio/sound.md": "", "audio/credits.md": ""}.items():
        (g / f).parent.mkdir(parents=True, exist_ok=True)
        (g / f).write_text(body, encoding="utf-8")
    assert sorted(prune_release_game(g)) == ["art/ref-objects.js", "art/style.md", "audio/sound.md"]
    assert sorted(p.relative_to(g).as_posix() for p in g.rglob("*") if p.is_file()) == [
        "art/art.js", "audio/credits.md", "audio/sound.js", "game.js", "index.html"]


# ---- 發布子圖(單獨模式) ----
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "good"
RCFG = {"configurable": {"thread_id": "release"}}


class Rel:
    def __init__(self, tmp_path, runner=None, renderer=None):
        self.project = tmp_path / "bubble"
        shutil.copytree(FIXTURE / "game", self.project / "game")
        (self.project / ".lab").mkdir()
        self.runner = runner or FakeRunner()
        self.renderer = renderer or FakeRenderer()
        self.info = tmp_path / "release-info.md"
        self.info.write_text("名稱: 捕泡手\n代號: bubble-catcher\n介紹: 跟著節拍戳泡泡。\n", encoding="utf-8")

    def call(self, inp):
        conn = sqlite3.connect(self.project / ".lab" / "release.sqlite", check_same_thread=False)
        try:
            g = build_release_graph(Deps(self.runner, NodeChecker(), self.renderer), SqliteSaver(conn))
            try:
                g.invoke(inp, RCFG)
                err = None
            except Exception as e:  # noqa: BLE001
                err = e
            return g.get_state(RCFG), err
        finally:
            conn.close()

    def start(self):
        return self.call({"project": str(self.project), "round_dir": "", "feedback": str(self.info),
                          "standalone": True})

    def pick(self, text="圖示: B\n主色: 2\n橫幅: A"):
        f = self.project / "release-pick.md"
        f.write_text(text, encoding="utf-8")
        return self.call(Command(resume={"choice": "pick", "feedback": str(f)}))


def calls(runner, kind):
    return sum(1 for k, _, _ in runner.calls if k == kind)


def test_release_pauses_with_options_page(tmp_path):
    rel = Rel(tmp_path)
    snap, err = rel.start()
    assert err is None, err
    v = snap.interrupts[0].value
    assert v["kind"] == "waiting_release_pick" and Path(v["options_page"]).exists()
    opts = rel.project / "release" / "options"
    for n in ("icon-a", "icon-b", "icon-c"):
        assert png_size(opts / f"{n}.png") == (512, 512)
    for n in ("banner-a", "banner-b", "banner-c"):
        assert png_size(opts / f"{n}.png") == (1680, 720)
    info = json.loads((opts / "info.json").read_text(encoding="utf-8"))
    assert info["name"] == "捕泡手" and info["code"] == "bubble-catcher" and info["touch"] is False
    assert info["ratio"] == "3:4" and info["ratio_site"] is False


def test_release_pick_finalizes_assets(tmp_path):
    rel = Rel(tmp_path)
    rel.start()
    snap, err = rel.pick()
    assert err is None and not snap.next
    assets = rel.project / "release" / "assets"
    assert not (assets / "share.png").exists()
    assert png_size(assets / "icon.png") == (512, 512) and png_size(assets / "banner.png") == (1680, 720)
    assert "#aaefd5" in (assets / "素材資訊.md").read_text(encoding="utf-8")
    site = json.loads((assets / "info.json").read_text(encoding="utf-8"))
    assert site["code"] == "bubble-catcher" and site["color"] == "#aaefd5" and "device" not in site
    w = snap.values["release_warnings"]  # 測試用的遊戲是直式 3:4、沒有觸控, 假繪圖的圖樣是白底: 比例、觸控、圖樣底色三條提醒
    assert len(w) == 3 and "3:4" in w[0] and "16:9" in w[0] and "觸控" in w[1] and "pattern.png" in w[2] and "#aaefd5" in w[2]
    assert png_size(assets / "pattern.png") == (256, 256)
    game = rel.project / "release" / "game"   # 定版時加上載入進度條, 接合檢查照樣讀得到程式
    assert "<!-- pvd-loader -->" in (game / "index.html").read_text(encoding="utf-8")
    result = NodeChecker().check(game, "deepen")
    assert result["ok"], result["errors"]


def test_release_redo_only_reruns_art(tmp_path):
    rel = Rel(tmp_path)
    rel.start()
    snap, err = rel.call(Command(resume={"choice": "redo"}))
    assert err is None and snap.interrupts[0].value["kind"] == "waiting_release_pick"
    assert calls(rel.runner, "release-art") == 2
    assert calls(rel.runner, "release-game") == 1 and calls(rel.runner, "release-info") == 1


def test_release_missing_option_fails(tmp_path):
    rel = Rel(tmp_path, runner=FakeRunner(drop_option="banner-c.html"))
    _, err = rel.start()
    assert isinstance(err, LabError) and "banner-c.html" in str(err)


def test_render_size_mismatch_fails(tmp_path):
    rel = Rel(tmp_path, renderer=FakeRenderer(wrong_size="icon-b"))
    _, err = rel.start()
    assert isinstance(err, LabError) and "icon-b.png" in str(err)


def test_release_bad_pick_errors(tmp_path):
    rel = Rel(tmp_path)
    rel.start()
    _, err = rel.pick("圖示: D\n主色: 2\n橫幅: A")
    assert isinstance(err, LabError) and "圖示" in str(err)


def test_release_keeps_source_game(tmp_path):
    rel = Rel(tmp_path)
    rel.start()
    assert "// release" in (rel.project / "release" / "game" / "game.js").read_text(encoding="utf-8")
    assert "// release" not in (rel.project / "game" / "game.js").read_text(encoding="utf-8")


def test_chrome_renderer_real(tmp_path):
    if not find_chrome():
        pytest.skip("沒有 Chrome")
    page = tmp_path / "p.html"
    page.write_text('<!doctype html><body style="margin:0;background:#4776c3"></body>', encoding="utf-8")
    ChromeRenderer().render(page, tmp_path / "p.png", (200, 100))
    assert png_size(tmp_path / "p.png") == (200, 100)


def test_touch_mode_reads_config_and_script_tag(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    assert touch_mode(g) is None
    (g / "touch.js").write_text("var CONFIG = {\n    mode: 'mouse',\n};", encoding="utf-8")
    (g / "index.html").write_text('<script src="game.js"></script>', encoding="utf-8")
    assert touch_mode(g) is None  # index.html 沒載入 touch.js
    (g / "index.html").write_text('<script src="game.js"></script>\n<script src="touch.js"></script>', encoding="utf-8")
    assert touch_mode(g) == "mouse"


def test_release_without_touch_layer_fails(tmp_path):
    rel = Rel(tmp_path, runner=FakeRunner(touch=None))
    _, err = rel.start()
    assert isinstance(err, LabError) and "觸控層" in str(err)


def test_asset_info_mobile_ratio(tmp_path):
    info = {**INFO, "ratio": "16:9", "ratio_site": True, "mobile_ratio": "16:9-21:9"}
    text = write_asset_info(tmp_path, info, COLORS[1]).read_text(encoding="utf-8")
    assert "| 遊戲畫面比例 | 電腦 16:9; 手機依螢幕 16:9～21:9 |" in text


def test_site_rule_warnings(tmp_path):
    (tmp_path / "audio").mkdir()
    (tmp_path / "game.js").write_text(
        "localStorage.setItem('ghost-echo:best', 1); localStorage.getItem(\"bcv19_best\");\n"
        "localStorage.clear(); window.open('x'); location.href = 'y'; if (location.href === 'z') {}\n", encoding="utf-8")
    (tmp_path / "audio" / "sound.js").write_text("try { sessionStorage.removeItem(`ghost-echo:muted`); } catch (e) {}", encoding="utf-8")
    w = site_rule_warnings(tmp_path, "ghost-echo")
    assert len(w) == 4
    assert any("bcv19_best" in x for x in w) and not any("ghost-echo:best" in x or "ghost-echo:muted" in x for x in w)
    assert any("清空" in x for x in w) and any("新視窗" in x for x in w) and any("改網址" in x for x in w)
    (tmp_path / "game.js").write_text("const top = 1; parent.postMessage({}, location.origin);", encoding="utf-8")
    assert site_rule_warnings(tmp_path, "ghost-echo") == []


# ---- 載入進度條 ----
NL = chr(10)


def _loader_game(tmp_path, index):
    g = tmp_path / "game"
    for f, body in {"index.html": index, "art/art.js": "a" * 10, "game.js": "g" * 20, "touch.js": "mode: 'keys'"}.items():
        (g / f).parent.mkdir(parents=True, exist_ok=True)
        (g / f).write_text(body, encoding="utf-8")
    return g


def test_add_loader_replaces_local_scripts_in_order(tmp_path):
    g = _loader_game(tmp_path, '<head><script src="https://cdn.x/lib.js"></script></head><body><canvas></canvas>' + NL +
                     '<script src="art/art.js"></script>' + NL + '<script src="game.js"></script>' + NL + '<script src="touch.js"></script>' + NL + '</body>')
    assert add_loader(g) == ["art/art.js", "game.js", "touch.js"]
    html = (g / "index.html").read_text(encoding="utf-8")
    assert '<script src="https://cdn.x/lib.js">' in html and '<script src="game.js">' not in html
    assert 'var FILES = [["art/art.js", 10], ["game.js", 20], ["touch.js", 12]];' in html
    assert html.index("<canvas>") < html.index("<!-- pvd-loader -->")
    assert touch_mode(g) == "keys"
    (g / "game.js").write_text("g" * 25, encoding="utf-8")   # 改了遊戲檔重跑: 只更新大小, 不重複加
    assert add_loader(g) == ["art/art.js", "game.js", "touch.js"]
    html = (g / "index.html").read_text(encoding="utf-8")
    assert html.count("<!-- pvd-loader -->") == 1 and '["game.js", 25]' in html


def test_add_loader_rejects_inline_script_after(tmp_path):
    g = _loader_game(tmp_path, '<script src="art/art.js"></script><script src="game.js"></script><script>start()</script>')
    with pytest.raises(ValueError):
        add_loader(g)


def test_add_loader_missing_file(tmp_path):
    g = _loader_game(tmp_path, '<script src="art/art.js"></script><script src="nope.js"></script>')
    with pytest.raises(FileNotFoundError):
        add_loader(g)


def test_loader_uses_page_background(tmp_path):
    from lab.loader import page_background
    assert page_background("<style>\nhtml,body{margin:0;background:#1a2b3c}</style>") == "#1a2b3c"
    assert page_background("<style>body { background-color: black; }</style>") == "black"
    assert page_background("<style>canvas{background:#fff}</style>") == "#111"
    g = _loader_game(tmp_path, '<style>body{background:#222}</style><script src="art/art.js"></script>')
    add_loader(g)
    assert "background:#222;color" in (g / "index.html").read_text(encoding="utf-8")


def _tile(path, fn, alpha=False):
    """用 fn(x, y) -> (r, g, b[, a]) 寫一張 256×256 PNG(每列用不同濾波, 順便測解碼)。"""
    import struct as st, zlib as zl
    bpp = 4 if alpha else 3
    raw = b""
    for y in range(256):
        line = b"".join(bytes(fn(x, y)[:bpp]) for x in range(256))
        f = y % 2  # 0 = 不濾波, 1 = Sub
        if f == 1:
            line = bytes((line[i] - (line[i - bpp] if i >= bpp else 0)) & 255 for i in range(len(line)))
        raw += bytes([f]) + line
    def chunk(t, b): return st.pack(">I", len(b)) + t + b + st.pack(">I", zl.crc32(t + b))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", st.pack(">IIBBBBB", 256, 256, 8, 6 if alpha else 2, 0, 0, 0))
                     + chunk(b"IDAT", zl.compress(raw)) + chunk(b"IEND", b""))


def test_pattern_problems(tmp_path):
    from lab.release import pattern_problems, png_pixels
    bg = (0xf2, 0x9c, 0xac)
    dots = lambda x, y: (0xe6, 0x8e, 0x9f) if (x % 64 - 32) ** 2 + (y % 64 - 32) ** 2 < 36 else bg  # 淡點, 64 的倍數會無縫
    _tile(tmp_path / "ok.png", dots)
    assert png_pixels(tmp_path / "ok.png")[2][32 * 256 + 32][:3] == (0xe6, 0x8e, 0x9f)
    assert pattern_problems(tmp_path / "ok.png", "#f29cac") == []
    assert any("底色" in p for p in pattern_problems(tmp_path / "ok.png", "#4776c3"))
    _tile(tmp_path / "hi.png", lambda x, y: (0, 0, 0) if x % 8 == 0 else bg)
    assert any("對比" in p for p in pattern_problems(tmp_path / "hi.png", "#f29cac"))
    _tile(tmp_path / "seam.png", lambda x, y: (bg[0] - x // 8, bg[1], bg[2]))  # 左到右漸層, 首尾差 31
    assert any("接縫" in p for p in pattern_problems(tmp_path / "seam.png", "#f29cac"))
    _tile(tmp_path / "alpha.png", lambda x, y: (*bg, 128 if x < 4 else 255), alpha=True)
    assert any("透明" in p for p in pattern_problems(tmp_path / "alpha.png", "#f29cac"))
    write_png(tmp_path / "small.png", 128, 128)
    assert "尺寸" in pattern_problems(tmp_path / "small.png", "#ffffff")[0]
