"""接合腳本: 正確樣本要過, 各種弄壞的樣本都要抓得到。"""
import shutil
from pathlib import Path

import pytest

from lab.checker import NodeChecker

GOOD = Path(__file__).parent / "fixtures" / "good"


@pytest.fixture
def game(tmp_path):
    dest = tmp_path / "game-a"
    shutil.copytree(GOOD, dest)
    return dest


def edit(path: Path, old: str, new: str):
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} 不在 {path.name}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def check(game, stage="polish"):
    return NodeChecker().check(game / "game", stage)


def steps(result):
    return {e["step"].split()[0] for e in result["errors"]}


def test_good_sample_passes(game):
    assert check(game) == {"ok": True, "errors": []}


def test_missing_draw_function(game):
    edit(game / "game/art/art.js", "drawCoin(ctx, state)", "drawCoinX(ctx, state)")
    r = check(game)
    assert not r["ok"]
    assert any("Art.drawCoin 不存在" in e["message"] for e in r["errors"])


def test_art_throws(game):
    edit(game / "game/art/art.js", "ctx.arc(", "undefinedThing.arc(")
    r = check(game)
    assert not r["ok"] and "art" in steps(r)


def test_game_load_error(game):
    edit(game / "game/game.js", "const ctx =", "const ctx = notDefined +")
    r = check(game)
    assert not r["ok"] and "load" in steps(r)


def test_runtime_error_in_frame(game):
    edit(game / "game/game.js", "c.y += 200 * dt;", "c.y += 200 * dt; if (state.score >= 0) c.boom.bang();")
    r = check(game)
    assert not r["ok"] and "frame" in steps(r)


def test_call_outside_interface(game):
    edit(game / "game/game.js", "Art.drawHud(ctx, state);", "Art.drawHud(ctx, state); if (Art.drawStar) Art.drawStar(ctx, state);")
    r = check(game)
    assert any("Art.drawStar" in e["message"] for e in r["errors"])


def test_unknown_sound_in_polish(game):
    edit(game / "game/game.js", "Sound.play('coin')", "Sound.play('jump')")
    assert any("jump" in e["message"] for e in check(game)["errors"])


def test_missing_charset(game):
    edit(game / "game/index.html", '<meta charset="utf-8">', "")
    assert "charset" in steps(check(game))


def test_canvas_size_mismatch(game):
    edit(game / "game/art/art.js", "width: 480", "width: 500")
    assert any("不符" in e["message"] for e in check(game)["errors"])


def test_missing_sound_js_only_matters_in_polish(game):
    edit(game / "game/index.html", '<script src="audio/sound.js"></script>', "")
    edit(game / "game/game.js", "Sound.init();", "")
    edit(game / "game/game.js", "Sound.play('coin');", "")
    edit(game / "game/game.js", "Sound.playMusic('main');", "")
    assert check(game, "explore")["ok"]
    assert not check(game, "polish")["ok"]
