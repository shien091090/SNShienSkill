"""流程走向: 用假執行器跑整張圖, 確認每條分支與中斷接回。"""
import sqlite3
from pathlib import Path

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from lab.checker import NodeChecker
from lab.fake import FakeRunner
from lab.graph import Deps, build_graph

CFG = {"configurable": {"thread_id": "main"}, "max_concurrency": 6}


class Lab:
    """每次動作都重新開連線、重新建圖, 等同 CLI 每次被呼叫都是新行程。"""

    def __init__(self, tmp_path, runner):
        self.project = tmp_path / "proj"
        self.project.mkdir()
        (self.project / ".lab").mkdir()
        self.idea = tmp_path / "idea.txt"
        self.idea.write_text("點擊收集掉落的金幣", encoding="utf-8")
        self.runner = runner

    def _graph(self, conn):
        return build_graph(Deps(self.runner, NodeChecker()), SqliteSaver(conn))

    def call(self, inp):
        conn = sqlite3.connect(self.project / ".lab" / "checkpoint.sqlite", check_same_thread=False)
        try:
            g = self._graph(conn)
            try:
                g.invoke(inp, CFG)
                err = None
            except Exception as e:  # noqa: BLE001 — 測錯誤處理
                err = e
            return g.get_state(CFG), err
        finally:
            conn.close()

    def start(self):
        return self.call({"project": str(self.project), "repo": "x", "idea_file": str(self.idea)})

    def resume(self, **ans):
        return self.call(Command(resume=ans))

    def feedback(self, round_dir):
        p = self.project / round_dir / "feedback.md"
        p.write_text("# 回饋\n", encoding="utf-8")
        return str(p)


def interrupt_of(snap):
    assert snap.interrupts, f"應該停在暫停點, 但 next={snap.next}"
    return snap.interrupts[0].value


def count(runner, kind, round_dir=None, game=None):
    return sum(1 for k, r, g in runner.calls
               if k == kind and (round_dir is None or r == round_dir) and (game is None or g == game))


def test_explore_round_pauses_for_feedback(tmp_path):
    lab = Lab(tmp_path, FakeRunner())
    snap, err = lab.start()
    assert err is None
    v = interrupt_of(snap)
    assert v["kind"] == "waiting_feedback" and v["round_dir"] == "explore-1"
    assert [g["id"] for g in v["games"]] == ["game-a", "game-b"]
    for g in v["games"]:
        assert Path(g["index_html"]).exists()
    assert (lab.project / "idea.md").read_text(encoding="utf-8").count("點擊收集掉落的金幣") == 1
    assert "等待試玩回饋" in (lab.project / "STATE.md").read_text(encoding="utf-8")
    assert count(lab.runner, "audio") == 0


def test_full_path_explore_deepen_polish_end(tmp_path):
    lab = Lab(tmp_path, FakeRunner())
    lab.start()
    snap, _ = lab.resume(choice="continue", feedback=lab.feedback("explore-1"))
    assert interrupt_of(snap)["round_dir"] == "explore-2"
    snap, _ = lab.resume(choice="next", feedback=lab.feedback("explore-2"))
    assert interrupt_of(snap)["round_dir"] == "deepen-1"
    snap, _ = lab.resume(choice="next", feedback=lab.feedback("deepen-1"))
    v = interrupt_of(snap)
    assert v["round_dir"] == "polish-1" and [g["id"] for g in v["games"]] == ["game"]
    assert count(lab.runner, "audio", "polish-1") == 1
    snap, err = lab.resume(choice="end", feedback=lab.feedback("polish-1"))
    assert err is None and snap.next == ()
    assert count(lab.runner, "review") == 4
    assert len(list((lab.project / "archive").glob("hypotheses.v*.md"))) == 4


@pytest.mark.parametrize("choice,stage", [("back-deepen", "deepen"), ("back-explore", "explore")])
def test_polish_can_go_back(tmp_path, choice, stage):
    lab = Lab(tmp_path, FakeRunner())
    lab.start()
    lab.resume(choice="next", feedback=lab.feedback("explore-1"))
    lab.resume(choice="next", feedback=lab.feedback("deepen-1"))
    snap, _ = lab.resume(choice=choice, feedback=lab.feedback("polish-1"))
    rd = interrupt_of(snap)["round_dir"]
    assert rd == f"{stage}-2"


def test_bugfix_returns_to_interview(tmp_path):
    lab = Lab(tmp_path, FakeRunner())
    lab.start()
    bugs = lab.project / "explore-1" / "bugs-1.md"
    bugs.write_text("- 點了沒反應", encoding="utf-8")
    snap, err = lab.resume(choice="fix", feedback=str(bugs), target="game-b")
    assert err is None
    v = interrupt_of(snap)
    assert v["kind"] == "waiting_feedback" and v["round_dir"] == "explore-1"
    assert count(lab.runner, "bugfix", game="game-b") == 1
    assert count(lab.runner, "review") == 0


def test_broken_art_goes_through_triage_and_only_art_redoes(tmp_path):
    lab = Lab(tmp_path, FakeRunner(break_once={("art", "game-b")}))
    snap, err = lab.start()
    assert err is None and interrupt_of(snap)["kind"] == "waiting_feedback"
    assert count(lab.runner, "triage", game="game-b") == 1
    assert count(lab.runner, "art-fix", game="game-b") == 1
    assert count(lab.runner, "rd-fix", game="game-b") == 0
    assert count(lab.runner, "triage", game="game-a") == 0


def test_triage_exhausted_then_retry_or_skip(tmp_path):
    runner = FakeRunner(break_once={("art", "game-b")})
    # art-fix 也一直壞: 讓重試用完
    original = runner._art_fix
    runner._art_fix = lambda ctx, broken: original(ctx, True)
    lab = Lab(tmp_path, runner)
    snap, _ = lab.start()
    v = interrupt_of(snap)
    assert v["kind"] == "build_failed" and list(v["failed"]) == ["game-b"]
    assert count(runner, "triage", game="game-b") == 2

    snap, _ = lab.resume(choice="retry")
    assert interrupt_of(snap)["kind"] == "build_failed"   # 還是壞的
    assert count(runner, "art", game="game-b") == 1       # retry 不從頭重做

    runner._art_fix = original
    snap, _ = lab.resume(choice="retry")
    v = interrupt_of(snap)
    assert v["kind"] == "waiting_feedback" and [g["id"] for g in v["games"]] == ["game-a", "game-b"]


def test_skip_failed_game(tmp_path):
    runner = FakeRunner(break_once={("art", "game-b")})
    original = runner._art_fix
    runner._art_fix = lambda ctx, broken: original(ctx, True)
    lab = Lab(tmp_path, runner)
    lab.start()
    snap, _ = lab.resume(choice="skip")
    v = interrupt_of(snap)
    assert v["kind"] == "waiting_feedback" and [g["id"] for g in v["games"]] == ["game-a"]


def test_crash_resumes_without_redoing_finished_work(tmp_path):
    lab = Lab(tmp_path, FakeRunner(fail_once={("rd", "game-a")}))
    snap, err = lab.start()
    assert err is not None and not snap.interrupts
    assert count(lab.runner, "design") == 1
    snap, err = lab.call(None)  # 不帶 choice 的 resume
    assert err is None and interrupt_of(snap)["kind"] == "waiting_feedback"
    assert count(lab.runner, "design") == 1
    assert count(lab.runner, "art", game="game-a") == 1
    assert count(lab.runner, "rd", game="game-a") == 2
    assert count(lab.runner, "art", game="game-b") == 1
    assert count(lab.runner, "rd", game="game-b") == 1


def test_design_must_produce_two_or_three_games(tmp_path):
    lab = Lab(tmp_path, FakeRunner(games_per_round=1))
    snap, err = lab.start()
    assert err is not None and "2~3" in str(err)
