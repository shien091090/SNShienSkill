"""每種任務的 prompt 都找得到檔、變數都有填上。"""
import re

import pytest

from lab.runner import render_prompt

CTX = {"project": "P", "stage": "explore", "round_dir": "explore-1", "round_no": 1, "prev_round": "無",
       "game": "game-a", "game_dir": "P/explore-1/game-a", "fix": "F", "report": "R", "out": "O",
       "roles": "art / rd", "bugs": "B", "feedback": "FB", "choice": "next"}

KINDS = [("design", s) for s in ("explore", "deepen", "polish")] + [
    (k, "explore") for k in ("art", "art-fix", "rd", "rd-fix", "audio", "audio-fix", "triage", "bugfix", "review")]


@pytest.mark.parametrize("kind,stage", KINDS)
def test_prompt_renders(kind, stage):
    text = render_prompt(kind, {**CTX, "stage": stage})
    left = re.findall(r"\$[a-z_]+", text)
    assert left == [], f"{kind} 還有沒填的變數: {left}"
    assert "game-studio-lab 共同守則" in text
