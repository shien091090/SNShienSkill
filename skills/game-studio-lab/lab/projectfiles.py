"""專案資料夾裡由程式維護的檔案: idea.md、hypotheses.md 骨架、STATE.md、archive。"""
import datetime
import re
import shutil
from pathlib import Path

from lab.state import STAGE_NAMES

HYPOTHESES_SKELETON = """# 玩法驗證文件

## 核心玩法(使用者指定, 每款都必須有)

## 已確認的體驗
### 想要
### 不要

## 機制清單
### 保留
### 避開

## 假設表
| 編號 | 機制 | 預期體驗 | 正/負 | 來源 | 驗證於 | 狀態 |
|---|---|---|---|---|---|---|

## 各款對應
| 輪次 | 款 | 主打體驗 | 驗哪幾條 |
|---|---|---|---|

## 修訂紀錄
"""


def today() -> str:
    return datetime.date.today().isoformat()


def write_idea(project: Path, idea_text: str) -> None:
    (project / "idea.md").write_text(
        f"# 玩法原文\n\n{idea_text.strip()}\n\n---\n收錄日期: {today()}\n", encoding="utf-8"
    )


def write_hypotheses_skeleton(project: Path) -> None:
    (project / "hypotheses.md").write_text(HYPOTHESES_SKELETON, encoding="utf-8")


def archive_hypotheses(project: Path) -> Path:
    """review 改寫前把現行驗證文件存成 archive/hypotheses.v<N>.md, N 接續既有最大號。"""
    archive = project / "archive"
    archive.mkdir(exist_ok=True)
    nums = [int(m.group(1)) for p in archive.glob("hypotheses.v*.md")
            if (m := re.match(r"hypotheses\.v(\d+)\.md$", p.name))]
    dest = archive / f"hypotheses.v{max(nums, default=0) + 1}.md"
    shutil.copyfile(project / "hypotheses.md", dest)
    return dest


def update_state_md(project: Path, state: dict, status: str, log: str | None = None) -> None:
    """STATE.md 給人看: 目前階段、輪次、狀態與事件紀錄。真正的進度在 .lab/checkpoint.sqlite。"""
    path = project / "STATE.md"
    old_log = []
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if "log:\n" in text:
            old_log = [ln for ln in text.split("log:\n", 1)[1].splitlines() if ln.startswith("- ")]
    if log:
        old_log.append(f"- {today()} {log}")
    rounds = state.get("rounds") or {}
    stage = state.get("stage", "explore")
    body = (
        f"stage: {stage}({STAGE_NAMES.get(stage, stage)})\n"
        f"rounds: 探索 {rounds.get('explore', 0)}, 深掘 {rounds.get('deepen', 0)}, 打磨 {rounds.get('polish', 0)}\n"
        f"current: {state.get('round_dir', '-')}\n"
        f"status: {status}\n"
        "log:\n" + "\n".join(old_log) + ("\n" if old_log else "")
    )
    path.write_text(body, encoding="utf-8")


def round_games(project: Path, round_dir: str) -> list[str]:
    """設計節點交稿後, 從資料夾讀出本輪實際有哪幾款(有 interface.json 才算)。"""
    base = project / round_dir
    return sorted(p.name for p in base.iterdir()
                  if p.is_dir() and (p / "interface.json").exists())
