"""CLI 端到端: 假執行器 + 本機 bare repo 當遠端, 確認每次停下來都 commit + push。"""
import json
import subprocess

import pytest

from lab import cli


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_FAKE_CLAUDE", "1")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    idea = tmp_path / "idea.txt"
    idea.write_text("點擊收集掉落的金幣", encoding="utf-8")
    return {"project": tmp_path / "proj", "remote": str(remote), "idea": str(idea), "tmp": tmp_path}


def call(capsys, *argv):
    code = cli.main([str(a) for a in argv])
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    return code, out


def remote_log(remote):
    r = subprocess.run(["git", "--git-dir", remote, "log", "--format=%s", "main"],
                       capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip().splitlines()


def test_start_resume_end(env, capsys):
    code, out = call(capsys, "start", env["project"], "--idea-file", env["idea"], "--repo", env["remote"])
    assert code == 0 and out["status"] == "waiting_feedback", out
    assert out["round_dir"] == "explore-1" and out["warnings"] == []
    assert remote_log(env["remote"]) == ["[feat] [proj] 1.建立專案 2.探索第1輪產出2款試玩版"]

    # 選擇不合法
    fb = env["project"] / "explore-1" / "feedback.md"
    fb.write_text("# 回饋", encoding="utf-8")
    code, out = call(capsys, "resume", env["project"], "--choice", "back-deepen", "--feedback", fb)
    assert code == 1 and "只能選" in out["error"]

    code, out = call(capsys, "resume", env["project"], "--choice", "next", "--feedback", fb)
    assert out["status"] == "waiting_feedback" and out["round_dir"] == "deepen-1"
    assert remote_log(env["remote"])[0] == "[feat] [proj] 1.探索第1輪依試玩回饋檢討假設 2.深掘第1輪產出2款試玩版"

    fb2 = env["project"] / "deepen-1" / "feedback.md"
    fb2.write_text("# 回饋", encoding="utf-8")
    code, out = call(capsys, "resume", env["project"], "--choice", "end", "--feedback", fb2)
    assert out["status"] == "done"
    assert remote_log(env["remote"])[0] == "[docs] [proj] 深掘第1輪依試玩回饋檢討假設"
    # 進度檔有進 git, WAL 不進
    tracked = subprocess.run(["git", "ls-files"], cwd=env["project"], capture_output=True, text=True).stdout
    assert ".lab/checkpoint.sqlite" in tracked and "sqlite-wal" not in tracked


def test_commit_message_when_resuming_interrupted_build():
    from pathlib import Path
    state = {"stage": "deepen", "rounds": {"explore": 1, "deepen": 1, "polish": 0},
             "round_dir": "deepen-1", "games": ["game-a", "game-b", "game-c"]}
    msg = cli.commit_message(Path("proj"), state, state, "waiting_feedback", None)
    assert msg == "[feat] [proj] 深掘第1輪產出3款試玩版"


def test_commit_message_for_next_polish_round_in_same_folder():
    from pathlib import Path
    before = {"stage": "polish", "rounds": {"explore": 1, "deepen": 2, "polish": 3},
              "round_dir": "polish", "games": ["game"]}
    after = {**before, "rounds": {"explore": 1, "deepen": 2, "polish": 4}}
    msg = cli.commit_message(Path("proj"), before, after, "waiting_feedback", "continue")
    assert msg == "[feat] [proj] 1.打磨第3輪依試玩回饋檢討假設 2.打磨第4輪產出1款試玩版"


def test_start_refuses_non_empty_folder(env, capsys):
    env["project"].mkdir()
    (env["project"] / "x.txt").write_text("x")
    code, out = call(capsys, "start", env["project"], "--idea-file", env["idea"], "--repo", env["remote"])
    assert code == 1 and "不是空資料夾" in out["error"]


def test_status(env, capsys):
    call(capsys, "start", env["project"], "--idea-file", env["idea"], "--repo", env["remote"])
    code, out = call(capsys, "status", env["project"])
    assert out["status"] == "waiting_feedback" and "fix" in out["allowed_choices"]


INFO = "名稱: 金幣雨\n代號: coin-rain\n介紹: 點擊收集掉落的金幣。\n"
PICK = "圖示: A\n主色: 3\n預覽圖: B\n"


def to_polish(env, capsys):
    call(capsys, "start", env["project"], "--idea-file", env["idea"], "--repo", env["remote"])
    for rd in ("explore-1", "deepen-1"):
        fb = env["project"] / rd / "feedback.md"
        fb.write_text("# 回饋", encoding="utf-8")
        call(capsys, "resume", env["project"], "--choice", "next", "--feedback", fb)


def write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_release_choice_validation(env, capsys):
    call(capsys, "start", env["project"], "--idea-file", env["idea"], "--repo", env["remote"])
    info = write(env["tmp"] / "info.md", INFO)
    code, out = call(capsys, "resume", env["project"], "--choice", "release", "--feedback", info)
    assert code == 1 and "只能選" in out["error"]
    fb = write(env["project"] / "explore-1" / "feedback.md", "# 回饋")
    call(capsys, "resume", env["project"], "--choice", "next", "--feedback", fb)
    fb = write(env["project"] / "deepen-1" / "feedback.md", "# 回饋")
    call(capsys, "resume", env["project"], "--choice", "next", "--feedback", fb)
    bad = write(env["tmp"] / "bad.md", "名稱: 金幣雨\n代號: coin-rain\n")
    code, out = call(capsys, "resume", env["project"], "--choice", "release", "--feedback", bad)
    assert code == 1 and "介紹" in out["error"]
    code, out = call(capsys, "resume", env["project"], "--choice", "release", "--feedback", info)
    assert out["status"] == "waiting_release_pick"
    code, out = call(capsys, "resume", env["project"], "--choice", "continue", "--feedback", info)
    assert code == 1 and "pick" in out["error"]
    badpick = write(env["tmp"] / "badpick.md", "圖示: A\n主色: 9\n預覽圖: B\n")
    code, out = call(capsys, "resume", env["project"], "--choice", "pick", "--feedback", badpick)
    assert code == 1 and "主色" in out["error"]


def test_release_commits(env, capsys):
    to_polish(env, capsys)
    info = write(env["project"] / "polish" / "release-info.md", INFO)
    code, out = call(capsys, "resume", env["project"], "--choice", "release", "--feedback", info)
    assert out["status"] == "waiting_release_pick" and out["options_page"].endswith("index.html")
    assert out["allowed_choices"] == ["pick", "redo"]
    assert remote_log(env["remote"])[0] == "[feat] [proj] 產出發布用遊戲與素材方案"
    call(capsys, "resume", env["project"], "--choice", "redo")
    assert remote_log(env["remote"])[0] == "[feat] [proj] 重做發布素材方案"
    pick = write(env["project"] / "polish" / "release-pick.md", PICK)
    code, out = call(capsys, "resume", env["project"], "--choice", "pick", "--feedback", pick)
    assert out["status"] == "waiting_feedback" and [w for w in out["warnings"] if "21:9" not in w] == []  # 測試用的遊戲是直式 3:4
    assert remote_log(env["remote"])[0] == "[feat] [proj] 發布素材定版"
    tracked = subprocess.run(["git", "ls-files"], cwd=env["project"], capture_output=True, text=True,
                             encoding="utf-8").stdout
    assert "release/assets/icon.png" in tracked


@pytest.fixture
def bubble(tmp_path, monkeypatch):
    import shutil
    from pathlib import Path
    monkeypatch.setenv("LAB_FAKE_CLAUDE", "1")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    proj = tmp_path / "WebGame_Bubble"
    shutil.copytree(Path(__file__).resolve().parent / "fixtures" / "good" / "game", proj / "game")
    for args in (["init", "-b", "main"], ["remote", "add", "origin", str(remote)], ["add", "-A"],
                 ["commit", "-m", "init"]):
        subprocess.run(["git", *args], cwd=proj, check=True, capture_output=True)
    return {"project": proj, "remote": str(remote), "tmp": tmp_path}


def test_standalone_release_flow(bubble, capsys):
    info = write(bubble["project"] / "release-info.md", INFO)
    code, out = call(capsys, "release", bubble["project"], "--info", info)
    assert out["status"] == "waiting_release_pick", out
    assert remote_log(bubble["remote"])[0] == "[feat] [WebGame_Bubble] 產出發布用遊戲與素材方案"
    code, out = call(capsys, "release", bubble["project"], "--info", info)
    assert code == 1 and "pick" in out["error"]
    pick = write(bubble["project"] / "release-pick.md", PICK)
    code, out = call(capsys, "release", bubble["project"], "--choice", "pick", "--feedback", pick)
    assert out["status"] == "done", out
    assets = bubble["project"] / "release" / "assets"
    assert (assets / "icon.png").exists() and (assets / "素材資訊.md").exists()
    assert remote_log(bubble["remote"])[0] == "[feat] [WebGame_Bubble] 發布素材定版"
    # 再發布一次: 停在挑選頁時舊的定版素材還在
    code, out = call(capsys, "release", bubble["project"], "--info", info)
    assert out["status"] == "waiting_release_pick" and (assets / "icon.png").exists()
    tracked = subprocess.run(["git", "ls-files"], cwd=bubble["project"], capture_output=True, text=True,
                             encoding="utf-8").stdout
    assert ".lab/release.sqlite" in tracked and ".lab/logs" not in tracked


def test_standalone_rejects_lab_project(env, capsys):
    call(capsys, "start", env["project"], "--idea-file", env["idea"], "--repo", env["remote"])
    code, out = call(capsys, "release", env["project"], "--info", write(env["tmp"] / "i.md", INFO))
    assert code == 1 and "resume --choice release" in out["error"]


def test_standalone_requires_game(tmp_path, capsys):
    code, out = call(capsys, "release", tmp_path, "--info", write(tmp_path / "i.md", INFO))
    assert code == 1 and "game/index.html" in out["error"]
