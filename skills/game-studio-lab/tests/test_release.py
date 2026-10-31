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
from lab.release_graph import build_release_graph
from lab.renderer import ChromeRenderer, FakeRenderer, find_chrome
from lab.release import (aspect_ratio, build_options_page, parse_release_info, parse_release_pick,
                         png_size, write_asset_info, write_png, prune_release_game,
                         write_site_info)

INFO = {"name": "幽影接力", "code": "ghost-echo", "intro": "和過去的自己接力闖關。", "time": "5–10 分鐘",
        "time_estimated": True, "ratio": "9:16", "ratio_site": False, "mobile": False}
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
    assert parse_release_pick("圖示: b\n主色: 2\n預覽圖: A") == {"icon": "B", "color": "2", "share": "A"}
    with pytest.raises(ValueError, match="主色"):
        parse_release_pick("圖示: B\n主色: 4\n預覽圖: A")


@pytest.mark.parametrize("w,h,want", [(1680, 720, ("21:9", True)), (1280, 720, ("16:9", False)), (720, 1280, ("9:16", False)),
                                      (480, 640, ("3:4", False))])
def test_aspect_ratio(w, h, want):
    assert aspect_ratio({"canvas": {"width": w, "height": h}}) == want
    assert aspect_ratio({}) == ("未知", False)


def test_png_roundtrip(tmp_path):
    write_png(tmp_path / "a.png", 512, 512)
    assert png_size(tmp_path / "a.png") == (512, 512)


def test_options_page_lists_all(tmp_path):
    (tmp_path / "options").mkdir()
    page = build_options_page(tmp_path, INFO, COLORS).read_text(encoding="utf-8")
    for s in ["圖示 A", "圖示 B", "圖示 C", "主色 1", "主色 2", "主色 3", "預覽圖 A", "預覽圖 C",
              "#f29cac", "#4776c3", "#e0c64f", "icon-a.png", "share-c.png", "幽影接力"]:
        assert s in page
    assert "<button" not in page and "<input" not in page


def test_asset_info_fields(tmp_path):
    text = write_asset_info(tmp_path, INFO, COLORS[1]).read_text(encoding="utf-8")
    for s in ["遊戲代號", "遊戲名稱", "遊戲介紹", "遊玩時長", "支援裝置", "遊戲主色", "遊戲畫面比例",
              "ghost-echo", "5–10 分鐘(估計)", "只支援電腦", "#4776c3", "#ffffff", "白色字",
              "不是 21:9"]:
        assert s in text
    assert "操作方式說明" not in text


def test_site_info_matches_website_format(tmp_path):
    info = {**INFO, "time": "5-10 分鐘", "mobile": True, "ratio": "16:9"}
    data = json.loads(write_site_info(tmp_path, info, {"bg": "#4AC", "fg": "#FFF"}).read_text(encoding="utf-8"))
    assert data == {"code": "ghost-echo", "name": "幽影接力", "intro": "和過去的自己接力闖關。", "time": "5–10 分鐘",
                    "mobile": True, "color": "#44aacc", "textColor": "#ffffff", "ratio": "16:9"}
    data = json.loads(write_site_info(tmp_path, INFO, COLORS[0]).read_text(encoding="utf-8"))
    assert data["textColor"] == "#2d2144" and data["mobile"] is False


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

    def pick(self, text="圖示: B\n主色: 2\n預覽圖: A"):
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
    for n in ("share-a", "share-b", "share-c"):
        assert png_size(opts / f"{n}.png") == (1200, 630)
    info = json.loads((opts / "info.json").read_text(encoding="utf-8"))
    assert info["name"] == "捕泡手" and info["code"] == "bubble-catcher" and info["mobile"] is False
    assert info["ratio"] == "3:4" and info["ratio_site"] is False


def test_release_pick_finalizes_assets(tmp_path):
    rel = Rel(tmp_path)
    rel.start()
    snap, err = rel.pick()
    assert err is None and not snap.next
    assets = rel.project / "release" / "assets"
    assert png_size(assets / "icon.png") == (512, 512) and png_size(assets / "share.png") == (1200, 630)
    assert "#aaefd5" in (assets / "素材資訊.md").read_text(encoding="utf-8")
    site = json.loads((assets / "info.json").read_text(encoding="utf-8"))
    assert site["code"] == "bubble-catcher" and site["color"] == "#aaefd5" and site["mobile"] is False
    w = snap.values["release_warnings"]  # 測試用的遊戲是直式 3:4, 只會有比例提醒
    assert len(w) == 1 and "3:4" in w[0] and "21:9" in w[0]


def test_release_redo_only_reruns_art(tmp_path):
    rel = Rel(tmp_path)
    rel.start()
    snap, err = rel.call(Command(resume={"choice": "redo"}))
    assert err is None and snap.interrupts[0].value["kind"] == "waiting_release_pick"
    assert calls(rel.runner, "release-art") == 2
    assert calls(rel.runner, "release-game") == 1 and calls(rel.runner, "release-info") == 1


def test_release_missing_option_fails(tmp_path):
    rel = Rel(tmp_path, runner=FakeRunner(drop_option="share-c.html"))
    _, err = rel.start()
    assert isinstance(err, LabError) and "share-c.html" in str(err)


def test_render_size_mismatch_fails(tmp_path):
    rel = Rel(tmp_path, renderer=FakeRenderer(wrong_size="icon-b"))
    _, err = rel.start()
    assert isinstance(err, LabError) and "icon-b.png" in str(err)


def test_release_bad_pick_errors(tmp_path):
    rel = Rel(tmp_path)
    rel.start()
    _, err = rel.pick("圖示: D\n主色: 2\n預覽圖: A")
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
