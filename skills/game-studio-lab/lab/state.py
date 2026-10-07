from typing import Annotated, TypedDict

STAGES = ("explore", "deepen", "polish")
STAGE_NAMES = {"explore": "探索", "deepen": "深掘", "polish": "打磨"}
NEXT_STAGE = {"explore": "deepen", "deepen": "polish"}

# 每款在接合腳本不過時, 最多叫幾次錯誤判定
MAX_TRIAGE = 2


def merge_results(old: dict | None, new: dict | None) -> dict:
    """各款製作結果以款名合併; 設計節點開新一輪時送 {"__reset__": True} 清空。"""
    if not new:
        return old or {}
    if new.get("__reset__"):
        return {}
    return {**(old or {}), **new}


class LabState(TypedDict, total=False):
    project: str
    repo: str
    idea_file: str
    stage: str
    rounds: dict
    round_dir: str
    games: list
    results: Annotated[dict, merge_results]
    choice: str
    feedback: str
    target: str
    warnings: list


class GameState(TypedDict, total=False):
    project: str
    stage: str
    round_dir: str
    game: str
    entry: str       # build: 美術 / RD 從頭做; check: 只重跑接合腳本(建置失敗後重試)
    fixes: dict      # 錯誤判定的退回對象與修改方向, 例 {"rd": "..."}
    check: dict
    retries: int
    results: Annotated[dict, merge_results]


class GameOutput(TypedDict):
    """子圖只把 results 交回主圖; 其他欄位若也交回, 多款同時寫 project / stage 會衝突。"""
    results: Annotated[dict, merge_results]
