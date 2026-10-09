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
