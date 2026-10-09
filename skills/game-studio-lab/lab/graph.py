"""LangGraph 流程: 設計 → 分岔製作(每款一個子圖)→ 試玩訪談 → 檢討假設 → 依選擇分支。

只有兩個地方會停下來等人(interrupt): join(有款建置失敗)與 interview(試玩訪談)。
git commit 不在節點裡做, 由 CLI 在每次停下來後統一做, 確保進度檔已寫完。
"""
import filecmp
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt

from lab.projectfiles import (archive_hypotheses, round_games, update_state_md,
                              write_hypotheses_skeleton, write_idea)
from lab.state import MAX_TRIAGE, NEXT_STAGE, STAGE_NAMES, GameOutput, GameState, LabState

PROJECT_GITIGNORE = ".lab/logs/\n.lab/*.sqlite-wal\n.lab/*.sqlite-shm\n"
POLISH_DIR = "polish"
ROUND_DIR_RE = re.compile(r"^(explore|deepen|polish)-\d+$")


def reset_build_marks(game_dir: Path) -> None:
    """打磨在同一個資料夾迭代: 開新一輪前清掉上一輪的完成標記與檢查結果, 否則美術 / RD 會被跳過。"""
    if not game_dir.exists():
        return
    for p in game_dir.glob(".done-*"):
        p.unlink()
    for name in ("check-report.json", "check-history.jsonl", "triage.json"):
        (game_dir / name).unlink(missing_ok=True)


def remove_round_dirs(project: Path) -> list[str]:
    removed = []
    for p in project.iterdir():
        if p.is_dir() and ROUND_DIR_RE.match(p.name):
            shutil.rmtree(p)
            removed.append(p.name)
    return sorted(removed)


def archive_polish_logs(project: Path, round_no: int) -> None:
    """打磨的試玩紀錄用完後收進 logs/round-<N>/, 下一輪 review 只讀 logs/ 底下新放進來的檔。"""
    logs = project / POLISH_DIR / "logs"
    files = list(logs.glob("*.json")) if logs.exists() else []
    if files:
        dest = logs / f"round-{round_no}"
        dest.mkdir(exist_ok=True)
        for f in files:
            shutil.move(str(f), dest / f.name)


class LabError(Exception):
    pass


@dataclass
class Deps:
    runner: object   # .run(kind, ctx) -> str
    checker: object  # .check(game_dir, stage) -> {"ok", "errors"}


def round_label(stage: str, rounds: dict) -> str:
    return f"{STAGE_NAMES[stage]}第{rounds.get(stage, 0)}輪"


def roles_for(stage: str) -> list[str]:
    return ["art", "rd", "audio"] if stage == "polish" else ["art", "rd"]


def build_game_graph(deps: Deps):
    """單款遊戲的製作子圖: 美術 ∥ RD(∥ 音效)→ 接合腳本 → 不過則錯誤判定 → 退回對象 → 接合腳本 ..."""

    def gdir(s) -> Path:
        return Path(s["project"]) / s["round_dir"] / s["game"]

    def ctx(s, **extra) -> dict:
        return {"project": s["project"], "stage": s["stage"], "round_dir": s["round_dir"],
                "game": s["game"], "game_dir": str(gdir(s)), **extra}

    def role_node(role):
        # 完成標記: 同一步裡別的角色當掉時, 接續會重跑整個子圖; 已交付的角色看到標記就跳過
        def node(s: GameState):
            fix = (s.get("fixes") or {}).get(role)
            if fix:
                deps.runner.run(f"{role}-fix", ctx(s, fix=fix,
                                                   report=str(gdir(s) / "check-report.json")))
                return {}
            marker = gdir(s) / f".done-{role}"
            if marker.exists():
                return {}
            deps.runner.run(role, ctx(s))
            marker.write_text("", encoding="utf-8")
            return {}
        return node

    def entry(s: GameState):
        if s.get("entry") == "check":
            return ["check"]
        return roles_for(s["stage"])

    def check(s: GameState):
        result = deps.checker.check(gdir(s) / "game", s["stage"])
        (gdir(s) / "check-report.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        # 每次結果都留底: check-report.json 會被下一次覆蓋, 事後查錯誤判定有沒有判錯要看這份
        with open(gdir(s) / "check-history.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"retries": s.get("retries", 0), **result}, ensure_ascii=False) + "\n")
        return {"check": result}

    def after_check(s: GameState):
        if s["check"]["ok"] or s.get("retries", 0) >= MAX_TRIAGE:
            return "finish"
        return "triage"

    def triage(s: GameState):
        out = gdir(s) / "triage.json"
        out.unlink(missing_ok=True)
        deps.runner.run("triage", ctx(s, report=str(gdir(s) / "check-report.json"), out=str(out),
                                      roles=" / ".join(roles_for(s["stage"]))))
        if not out.exists():
            raise LabError(f"{s['round_dir']}/{s['game']} 錯誤判定沒有寫出 triage.json")
        decision = json.loads(out.read_text(encoding="utf-8"))
        targets = {k: v for k, v in (decision.get("targets") or {}).items()
                   if k in roles_for(s["stage"]) and v}
        if not targets:
            raise LabError(f"{s['round_dir']}/{s['game']} 錯誤判定沒有指出退回對象: {decision}")
        return {"fixes": targets, "retries": s.get("retries", 0) + 1}

    def after_triage(s: GameState):
        return list(s["fixes"].keys())

    def finish(s: GameState):
        ok = s["check"]["ok"]
        return {"results": {s["game"]: {"status": "ok" if ok else "failed",
                                        "errors": s["check"]["errors"],
                                        "retries": s.get("retries", 0)}}}

    g = StateGraph(GameState, output_schema=GameOutput)
    for role in ("art", "rd", "audio"):
        g.add_node(role, role_node(role))
        g.add_edge(role, "check")
    g.add_node("check", check)
    g.add_node("triage", triage)
    g.add_node("finish", finish)
    g.add_conditional_edges(START, entry, ["art", "rd", "audio", "check"])
    g.add_conditional_edges("check", after_check, ["triage", "finish"])
    g.add_conditional_edges("triage", after_triage, ["art", "rd", "audio"])
    g.add_edge("finish", END)
    return g.compile()


def build_graph(deps: Deps, checkpointer=None):
    game_graph = build_game_graph(deps)

    def project_of(s) -> Path:
        return Path(s["project"])

    def setup(s: LabState):
        project = project_of(s)
        write_idea(project, Path(s["idea_file"]).read_text(encoding="utf-8"))
        write_hypotheses_skeleton(project)
        (project / ".gitignore").write_text(PROJECT_GITIGNORE, encoding="utf-8")
        rounds = {"explore": 0, "deepen": 0, "polish": 0}
        update_state_md(project, {"stage": "explore", "rounds": rounds}, "建立專案", "建立專案, 玩法寫入 idea.md")
        return {"stage": "explore", "rounds": rounds, "warnings": []}

    def design(s: LabState):
        project, stage = project_of(s), s["stage"]
        rounds = dict(s["rounds"])
        rounds[stage] += 1
        # 打磨固定在同一個資料夾迭代; 探索 / 深掘每輪一個資料夾
        round_dir = POLISH_DIR if stage == "polish" else f"{stage}-{rounds[stage]}"
        (project / round_dir).mkdir(parents=True, exist_ok=True)
        if stage == "polish":
            reset_build_marks(project / POLISH_DIR / "game")
        deps.runner.run("design", {"project": str(project), "stage": stage, "round_dir": round_dir,
                                   "round_no": rounds[stage], "prev_round": s.get("round_dir") or "無"})
        games = round_games(project, round_dir)
        if stage == "polish" and games != ["game"]:
            raise LabError(f"打磨階段應只有一款 game/, 實際: {games}")
        if stage != "polish" and not 2 <= len(games) <= 3:
            raise LabError(f"{round_dir} 應有 2~3 款(含 interface.json), 實際: {games}")
        for g in games:
            # 探索 / 深掘用說明頁(guide.md); 打磨改用開始畫面 + 嵌入式新手教學, 寫在 spec.md
            for f in ("spec.md",) if stage == "polish" else ("spec.md", "guide.md"):
                if not (project / round_dir / g / f).exists():
                    raise LabError(f"{round_dir}/{g} 缺 {f}")
        if stage == "polish":
            # 底版已由設計搬進 polish/, 探索 / 深掘與舊版編號打磨的資料夾不再需要(git 留有紀錄)
            remove_round_dirs(project)
        label = round_label(stage, rounds)
        update_state_md(project, {**s, "rounds": rounds, "round_dir": round_dir}, "製作中",
                        f"{label}設計完成, {len(games)} 款: {', '.join(games)}")
        return {"rounds": rounds, "round_dir": round_dir, "games": games,
                "results": {"__reset__": True}}

    def game_input(s: LabState, game: str, entry: str) -> dict:
        return {"project": s["project"], "stage": s["stage"], "round_dir": s["round_dir"],
                "game": game, "entry": entry, "retries": 0, "fixes": {}}

    def fanout(s: LabState):
        return [Send("build_game", game_input(s, g, "build")) for g in s["games"]]

    def join(s: LabState):
        failed = [g for g in s["games"] if (s.get("results") or {}).get(g, {}).get("status") != "ok"]
        if not failed:
            return Command(goto="interview")
        update_state_md(project_of(s), s, "建置失敗, 等使用者決定")
        ans = interrupt({"kind": "build_failed",
                         "failed": {g: (s.get("results") or {}).get(g, {}).get("errors") for g in failed}})
        if ans["choice"] == "retry":
            return Command(goto=[Send("build_game", game_input(s, g, "check")) for g in failed])
        games = [g for g in s["games"] if g not in failed]
        if not games:
            raise LabError("這輪沒有任何一款做成")
        update_state_md(project_of(s), s, "製作中", f"略過建置失敗的 {', '.join(failed)}")
        return Command(goto="interview", update={"games": games})

    def interview(s: LabState):
        project = project_of(s)
        update_state_md(project, s, "等待試玩回饋")
        ans = interrupt({
            "kind": "waiting_feedback", "stage": s["stage"], "round_dir": s["round_dir"],
            "games": [{"id": g, "index_html": str(project / s["round_dir"] / g / "game" / "index.html")}
                      for g in s["games"]],
        })
        update = {"choice": ans["choice"], "feedback": ans.get("feedback", ""), "target": ans.get("target", "")}
        return Command(goto="bugfix" if ans["choice"] == "fix" else "review", update=update)

    def bugfix(s: LabState):
        project, game = project_of(s), s["target"]
        gdir = project / s["round_dir"] / game
        base = {"project": str(project), "stage": s["stage"], "round_dir": s["round_dir"],
                "game": game, "game_dir": str(gdir)}
        deps.runner.run("bugfix", {**base, "bugs": s["feedback"]})
        for attempt in range(2):
            result = deps.checker.check(gdir / "game", s["stage"])
            (gdir / "check-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
            if result["ok"]:
                break
            if attempt == 0:
                deps.runner.run("rd-fix", {**base, "fix": "修 bug 後接合腳本沒過, 錯誤見報告",
                                           "report": str(gdir / "check-report.json")})
        else:
            raise LabError(f"{s['round_dir']}/{game} 修 bug 後接合腳本仍不過: {result['errors']}")
        update_state_md(project, s, "等待試玩回饋", f"{round_label(s['stage'], s['rounds'])} {game} 修 bug 完成")
        return Command(goto="interview")

    def review(s: LabState):
        project, stage, choice = project_of(s), s["stage"], s["choice"]
        hyp = project / "hypotheses.md"
        archived = sorted((project / "archive").glob("hypotheses.v*.md")) if (project / "archive").exists() else []
        if not any(filecmp.cmp(hyp, a, shallow=False) for a in archived):
            archive_hypotheses(project)
        deps.runner.run("review", {"project": str(project), "stage": stage, "round_dir": s["round_dir"],
                                   "feedback": s["feedback"], "choice": choice})
        if s["round_dir"] == POLISH_DIR:
            archive_polish_logs(project, s["rounds"]["polish"])
        new_stage = {"continue": stage, "end": stage, "back-deepen": "deepen",
                     "back-explore": "explore"}.get(choice) or NEXT_STAGE[stage]
        label = round_label(stage, s["rounds"])
        status = "結束" if choice == "end" else "製作中"
        update_state_md(project, {**s, "stage": new_stage}, status, f"{label}檢討假設完成, 選擇: {choice}")
        return {"stage": new_stage}

    def after_review(s: LabState):
        return END if s["choice"] == "end" else "design"

    g = StateGraph(LabState)
    g.add_node("setup", setup)
    g.add_node("design", design)
    # 子圖直接當節點掛上, 才會被進度檔記錄: 某款中途當掉, 接續時已完成的美術 / RD 不重做
    g.add_node("build_game", game_graph)
    g.add_node("join", join)
    g.add_node("interview", interview)
    g.add_node("bugfix", bugfix)
    g.add_node("review", review)
    g.add_edge(START, "setup")
    g.add_edge("setup", "design")
    g.add_conditional_edges("design", fanout, ["build_game"])
    g.add_edge("build_game", "join")
    g.add_conditional_edges("review", after_review, ["design", END])
    return g.compile(checkpointer=checkpointer)
