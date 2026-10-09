"""入口 skill 呼叫的指令列。每次呼叫跑到下一個暫停點, 然後 commit + push, stdout 最後一行印狀態 JSON。

  python -m lab start  <專案> --idea-file <檔> --repo <url>
  python -m lab resume <專案> [--choice ...] [--feedback <檔>] [--target <款>]
  python -m lab status <專案>
"""
import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from lab.checker import NodeChecker
from lab.gitops import Git, SetupError
from lab.graph import Deps, build_graph, round_label
from lab.state import STAGE_NAMES

# 同時跑的 claude 上限; 記憶體吃緊時用 LAB_MAX_CONCURRENCY=1 改成一次一個
CFG = {"configurable": {"thread_id": "main"},
       "max_concurrency": int(os.environ.get("LAB_MAX_CONCURRENCY", "6"))}

FEEDBACK_CHOICES = {
    "explore": {"continue", "next", "end", "fix"},
    "deepen": {"continue", "next", "end", "fix"},
    "polish": {"continue", "end", "fix", "back-deepen", "back-explore"},
}
FAILED_CHOICES = {"retry", "skip"}


def make_deps() -> Deps:
    if os.environ.get("LAB_FAKE_CLAUDE") == "1":
        from lab.fake import FakeRunner
        return Deps(FakeRunner(), NodeChecker())
    from lab.runner import ClaudeRunner
    return Deps(ClaudeRunner(), NodeChecker())


class Session:
    def __init__(self, project: Path, deps: Deps):
        self.conn = sqlite3.connect(project / ".lab" / "checkpoint.sqlite", check_same_thread=False)
        self.graph = build_graph(deps, SqliteSaver(self.conn))

    def snapshot(self):
        return self.graph.get_state(CFG)

    def close(self):
        self.conn.close()


def report(project: Path, snap, error: str | None = None, warnings: list | None = None) -> dict:
    values = snap.values if snap else {}
    out = {"status": "done", "stage": values.get("stage"), "round_dir": values.get("round_dir"),
           "games": [], "warnings": list(warnings or []), "error": error}
    if error:
        out["status"] = "error"
    elif snap and snap.interrupts:
        v = snap.interrupts[0].value
        out["status"] = v["kind"]
        if v["kind"] == "waiting_feedback":
            out["games"] = v["games"]
            out["allowed_choices"] = sorted(FEEDBACK_CHOICES[v["stage"]])
        else:
            out["failed"] = v["failed"]
            out["allowed_choices"] = sorted(FAILED_CHOICES)
    elif snap and snap.next:
        out["status"] = "paused"
    return out


def commit_message(project: Path, before: dict, after: dict, status: str, choice: str | None) -> str:
    name = project.name
    if status == "error":
        return f"[other] [{name}] 流程中途停止, 保留目前進度"
    if choice == "fix":
        return f"[fix] [{name}] 修正{round_label(after['stage'], after['rounds'])}{after.get('target', '')}試玩回報的問題"
    parts = []
    if not before.get("round_dir"):
        parts.append("建立專案")
    if choice in FAILED_CHOICES:
        parts.append(f"{round_label(after['stage'], after['rounds'])}建置失敗後"
                     f"{'重試' if choice == 'retry' else '略過失敗的款'}")
    elif choice:
        parts.append(f"{round_label(before['stage'], before['rounds'])}依試玩回饋檢討假設")
    # 打磨固定同一個資料夾, 所以用輪次數判斷有沒有開新一輪, 不能只看資料夾名
    new_round = bool(after.get("round_dir")) and (
        after.get("round_dir") != before.get("round_dir")
        or (after.get("rounds") or {}) != (before.get("rounds") or {}))
    if new_round:
        parts.append(f"{round_label(after['stage'], after['rounds'])}產出{len(after.get('games') or [])}款試玩版")
    if not parts:
        # 中斷後不帶 choice 接續: 這次跑完的通常是本輪製作
        if status == "waiting_feedback":
            new_round = True
            parts.append(f"{round_label(after['stage'], after['rounds'])}產出{len(after.get('games') or [])}款試玩版")
        else:
            parts.append("接續中斷的流程")
    prefix = "[feat]" if new_round or choice in FAILED_CHOICES else "[docs]"
    body = parts[0] if len(parts) == 1 else " ".join(f"{i}.{p}" for i, p in enumerate(parts, 1))
    return f"{prefix} [{name}] {body}"


def run(project: Path, inp, choice: str | None = None) -> dict:
    session = Session(project, make_deps())
    before = dict(session.snapshot().values or {})
    error = None
    try:
        session.graph.invoke(inp, CFG)
    except Exception as e:  # noqa: BLE001 — 錯誤原文交給使用者
        error = f"{type(e).__name__}: {e}"
    snap = session.snapshot()
    session.close()  # 關掉連線才會把 WAL 寫回 sqlite, 之後 commit 的才是完整進度
    out = report(project, snap, error)
    msg = commit_message(project, before, dict(snap.values or {}), out["status"], choice)
    try:
        warn = Git().commit_push(project, msg)
    except Exception as e:  # noqa: BLE001
        warn = f"commit 失敗: {e}"
    if warn:
        out["warnings"].append(warn)
    return out


def cmd_start(args) -> dict:
    project = Path(args.project).resolve()
    if project.exists() and any(project.iterdir()):
        raise SetupError(f"{project} 已存在且不是空資料夾; 要接續既有專案請用 resume")
    if not Git().remote_is_empty(args.repo):
        raise SetupError(f"遠端 repo {args.repo} 已經有內容, 請給一個空的 repo")
    idea = Path(args.idea_file).resolve()
    if not idea.exists():
        raise SetupError(f"找不到玩法檔 {idea}")
    (project / ".lab").mkdir(parents=True, exist_ok=True)
    Git().init(project, args.repo)
    return run(project, {"project": str(project), "repo": args.repo, "idea_file": str(idea)})


def cmd_resume(args) -> dict:
    project = Path(args.project).resolve()
    if not (project / ".lab" / "checkpoint.sqlite").exists():
        raise SetupError(f"{project} 不是 game-studio-lab 專案(沒有 .lab/checkpoint.sqlite)")
    session = Session(project, make_deps())
    snap = session.snapshot()
    session.close()
    if not snap.interrupts:
        if args.choice:
            raise SetupError("目前不在暫停點, 不需要 --choice; 直接 resume 會從上次失敗的節點接著跑")
        if not snap.next:
            raise SetupError("流程已經結束")
        return run(project, None)
    v = snap.interrupts[0].value
    if not args.choice:
        raise SetupError(f"目前停在 {v['kind']}, 需要 --choice")
    if v["kind"] == "waiting_feedback":
        allowed = FEEDBACK_CHOICES[v["stage"]]
        if args.choice not in allowed:
            raise SetupError(f"{STAGE_NAMES[v['stage']]}階段只能選: {', '.join(sorted(allowed))}")
        if not args.feedback or not Path(args.feedback).exists():
            raise SetupError("需要 --feedback 指向已寫好的回饋檔(fix 時是 bug 清單)")
        if args.choice == "fix" and args.target not in [g["id"] for g in v["games"]]:
            raise SetupError(f"fix 需要 --target, 可選: {', '.join(g['id'] for g in v['games'])}")
    elif args.choice not in FAILED_CHOICES:
        raise SetupError("建置失敗時只能選 retry 或 skip")
    ans = {"choice": args.choice}
    if args.feedback:
        ans["feedback"] = str(Path(args.feedback).resolve())
    if args.target:
        ans["target"] = args.target
    return run(project, Command(resume=ans), args.choice)


def cmd_status(args) -> dict:
    project = Path(args.project).resolve()
    session = Session(project, make_deps())
    snap = session.snapshot()
    session.close()
    return report(project, snap)


def cmd_probe_models(args) -> dict:
    from lab.runner import probe_models
    return {"status": "done", "models": probe_models(Path.cwd()), "warnings": []}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="lab")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("project")
    s.add_argument("--idea-file", required=True)
    s.add_argument("--repo", required=True)
    r = sub.add_parser("resume")
    r.add_argument("project")
    r.add_argument("--choice")
    r.add_argument("--feedback")
    r.add_argument("--target")
    st = sub.add_parser("status")
    st.add_argument("project")
    sub.add_parser("probe-models")
    args = p.parse_args(argv)
    try:
        out = {"start": cmd_start, "resume": cmd_resume, "status": cmd_status,
               "probe-models": cmd_probe_models}[args.cmd](args)
    except SetupError as e:
        out = {"status": "error", "error": str(e), "warnings": []}
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out["status"] != "error" else 1
