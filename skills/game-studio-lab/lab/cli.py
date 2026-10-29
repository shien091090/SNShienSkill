"""入口 skill 呼叫的指令列。每次呼叫跑到下一個暫停點, 然後 commit + push, stdout 最後一行印狀態 JSON。

  python -m lab start  <專案> --idea-file <檔> --repo <url>
  python -m lab resume <專案> [--choice ...] [--feedback <檔>] [--target <款>]
  python -m lab status <專案>
  python -m lab release <資料夾> [--info <檔>] [--choice pick|redo] [--feedback <檔>]  (非 lab 專案的發布)
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
from lab.release import parse_release_info, parse_release_pick
from lab.release_graph import build_release_graph
from lab.state import STAGE_NAMES

# 同時跑的 claude 上限; 記憶體吃緊時用 LAB_MAX_CONCURRENCY=1 改成一次一個
CFG = {"configurable": {"thread_id": "main"},
       "max_concurrency": int(os.environ.get("LAB_MAX_CONCURRENCY", "6"))}

FEEDBACK_CHOICES = {
    "explore": {"continue", "next", "end", "fix"},
    "deepen": {"continue", "next", "end", "fix"},
    "polish": {"continue", "end", "fix", "back-deepen", "back-explore", "release"},
}
FAILED_CHOICES = {"retry", "skip"}
PICK_CHOICES = {"pick", "redo"}
RELEASE_CFG = {"configurable": {"thread_id": "release"}}


def make_deps() -> Deps:
    if os.environ.get("LAB_FAKE_CLAUDE") == "1":
        from lab.fake import FakeRunner
        from lab.renderer import FakeRenderer
        return Deps(FakeRunner(), NodeChecker(), FakeRenderer())
    from lab.runner import ClaudeRunner
    return Deps(ClaudeRunner(), NodeChecker())


class Session:
    """release=True: 非 lab 專案的單獨發布, 進度檔另存 .lab/release.sqlite, 只跑發布子圖。"""

    def __init__(self, project: Path, deps: Deps, release: bool = False):
        db = "release.sqlite" if release else "checkpoint.sqlite"
        self.conn = sqlite3.connect(project / ".lab" / db, check_same_thread=False)
        builder = build_release_graph if release else build_graph
        self.graph = builder(deps, SqliteSaver(self.conn))
        self.cfg = RELEASE_CFG if release else CFG

    def snapshot(self):
        return self.graph.get_state(self.cfg)

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
        elif v["kind"] == "waiting_release_pick":
            out["options_page"] = v["options_page"]
            out["allowed_choices"] = sorted(PICK_CHOICES)
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
    release_msg = {"release": "產出發布用遊戲與素材方案", "redo": "重做發布素材方案", "pick": "發布素材定版",
                   "release-resume": "接續中斷的發布流程"}
    if choice in release_msg:
        return f"[feat] [{name}] {release_msg[choice]}"
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


def run(project: Path, inp, choice: str | None = None, release: bool = False) -> dict:
    session = Session(project, make_deps(), release)
    before = dict(session.snapshot().values or {})
    error = None
    try:
        session.graph.invoke(inp, session.cfg)
    except Exception as e:  # noqa: BLE001 — 錯誤原文交給使用者
        error = f"{type(e).__name__}: {e}"
    snap = session.snapshot()
    session.close()  # 關掉連線才會把 WAL 寫回 sqlite, 之後 commit 的才是完整進度
    out = report(project, snap, error)
    if choice == "pick" and not error:
        out["warnings"].extend((snap.values or {}).get("release_warnings") or [])
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


def check_user_file(path: str | None, parse) -> None:
    """發布資訊 / 挑選結果檔先在這裡驗, 格式錯就不進流程。"""
    if not path or not Path(path).exists():
        raise SetupError(f"找不到檔案 {path}")
    try:
        parse(Path(path).read_text(encoding="utf-8"))
    except ValueError as e:
        raise SetupError(str(e)) from e


def check_pick(args) -> None:
    if args.choice not in PICK_CHOICES:
        raise SetupError("停在挑選發布方案, 只能選 pick(交挑選結果)或 redo(重做方案)")
    if args.choice == "pick":
        check_user_file(args.feedback, parse_release_pick)


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
        if args.choice == "release":
            check_user_file(args.feedback, parse_release_info)
    elif v["kind"] == "waiting_release_pick":
        check_pick(args)
    elif args.choice not in FAILED_CHOICES:
        raise SetupError("建置失敗時只能選 retry 或 skip")
    ans = {"choice": args.choice}
    if args.feedback:
        ans["feedback"] = str(Path(args.feedback).resolve())
    if args.target:
        ans["target"] = args.target
    return run(project, Command(resume=ans), args.choice)


STANDALONE_GITIGNORE = "logs/\n*.sqlite-wal\n*.sqlite-shm\n"


def cmd_release(args) -> dict:
    """非 lab 專案(遊戲在 <資料夾>/game/)的單獨發布; lab 專案改在打磨停點選 release。"""
    project = Path(args.project).resolve()
    if (project / ".lab" / "checkpoint.sqlite").exists():
        raise SetupError(f"{project} 是 game-studio-lab 專案, 請在打磨停點用 resume --choice release")
    if not (project / "game" / "index.html").exists():
        raise SetupError(f"{project} 底下沒有 game/index.html")
    if not (project / ".git").exists():
        raise SetupError(f"{project} 不是 git repo, 發布結果無法 commit")
    (project / ".lab").mkdir(exist_ok=True)
    if not (project / ".lab" / ".gitignore").exists():
        (project / ".lab" / ".gitignore").write_text(STANDALONE_GITIGNORE, encoding="utf-8")
    session = Session(project, make_deps(), release=True)
    snap = session.snapshot()
    session.close()
    if snap.interrupts:
        if args.info:
            raise SetupError("目前停在挑選發布方案, 請先 --choice pick 或 redo")
        check_pick(args)
        ans = {"choice": args.choice}
        if args.feedback:
            ans["feedback"] = str(Path(args.feedback).resolve())
        return run(project, Command(resume=ans), args.choice, release=True)
    if args.choice:
        raise SetupError("目前沒有停在挑選發布方案, 不需要 --choice")
    if args.info:
        check_user_file(args.info, parse_release_info)
        return run(project, {"project": str(project), "round_dir": "", "standalone": True,
                             "feedback": str(Path(args.info).resolve())}, "release", release=True)
    if snap.next:
        return run(project, None, "release-resume", release=True)
    raise SetupError("需要 --info 指向發布資訊檔")


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
    rl = sub.add_parser("release")
    rl.add_argument("project")
    rl.add_argument("--info")
    rl.add_argument("--choice")
    rl.add_argument("--feedback")
    args = p.parse_args(argv)
    try:
        out = {"start": cmd_start, "resume": cmd_resume, "status": cmd_status, "release": cmd_release,
               "probe-models": cmd_probe_models}[args.cmd](args)
    except SetupError as e:
        out = {"status": "error", "error": str(e), "warnings": []}
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out["status"] != "error" else 1
