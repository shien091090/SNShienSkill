"""視覺設計節點: 挑底版 + 列元素清單 → 等使用者確認 → 每個元素出 3 個方案 → 方案頁 → 等使用者挑 → 寫視覺方向。

深掘選 next 檢討假設後、打磨第一輪設計前跑一次(已有 visual/direction.md 就不再跑)。
美術方案一個元素起一次 claude -p, 預設依序跑(並行容易吃光記憶體); 環境變數 LAB_VISUAL_PARALLEL=N 可同時跑 N 個元素
(記憶體充足時用)。完成標記讓中斷接續時跳過已出好的元素; 並行時某個元素失敗, 其他元素照樣跑完並寫標記, 最後才報錯。
設計見 docs/2026-11-19-visual-design-stage-design.md。

不包成子圖: 同一個子圖裡有兩個停點時, 中途當掉後接續會把上一個停點的回答錯配給下一個停點, 所以每步都是主圖節點。
"""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from langgraph.types import Command, interrupt

from lab.graph import LabError
from lab.projectfiles import update_state_md
from lab.visual import (OPTION_IDS, build_visual_page, missing_options, parse_elements, parse_visual_pick,
                        write_direction)

VISUAL_DIR = "visual"


def visual_dir(s) -> Path:
    return Path(s["project"]) / VISUAL_DIR


def load_elements(s) -> dict:
    path = visual_dir(s) / "elements.md"
    if not path.exists():
        raise LabError("視覺設計沒有寫出 visual/elements.md")
    try:
        parsed = parse_elements(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise LabError(f"visual/elements.md 格式不對: {e}") from e
    art = Path(s["project"]) / parsed["base"] / "game" / "art" / "art.js"
    if not art.exists():
        raise LabError(f"底版 {parsed['base']} 找不到 game/art/art.js")
    return parsed


def add_visual_nodes(g, deps, done: str) -> str:
    """把視覺設計各步加進主圖 g, 定案後接到 done 節點; 回傳入口節點名。round_dir 是深掘最後一輪(設計從這裡挑底版)。"""

    def list_elements(s):
        vdir = visual_dir(s)
        (vdir / "options").mkdir(parents=True, exist_ok=True)
        deps.runner.run("design", {"project": s["project"], "stage": "visual", "round_dir": s["round_dir"],
                                   "visual_dir": str(vdir)})
        load_elements(s)
        update_state_md(Path(s["project"]), s, "視覺設計: 等使用者確認元素清單", "視覺設計列出核心視覺元素")
        return {}

    def confirm(s):
        interrupt({"kind": "waiting_visual_list", "elements": str(visual_dir(s) / "elements.md")})
        # 主 session 依使用者意見直接改了 elements.md, 這裡重新讀
        return {"visual_base": load_elements(s)["base"]}

    def art(s):
        vdir, parsed = visual_dir(s), load_elements(s)
        opts = vdir / "options"
        base_dir = Path(s["project"]) / parsed["base"]

        def one(el):
            redo = opts / f"{el['code']}-redo.md"
            deps.runner.run("visual-art", {
                "project": s["project"], "stage": "visual", "visual_dir": str(vdir), "base_dir": str(base_dir),
                "element": el["code"], "element_name": el["name"], "element_kind": el["kind"],
                "element_content": el["content"], "element_why": el["why"] or "無",
                "redo_note": redo.read_text(encoding="utf-8").strip() if redo.exists() else "無"})
            missing = missing_options(opts, [el["code"]])
            if missing:
                raise LabError(f"元素 {el['code']} 的方案缺檔: {', '.join(missing)}")
            (opts / f".done-{el['code']}").write_text("", encoding="utf-8")

        todo = [el for el in parsed["elements"] if not (opts / f".done-{el['code']}").exists()]
        workers = max(1, int(os.environ.get("LAB_VISUAL_PARALLEL", "1") or 1))
        if workers == 1:
            for el in todo:
                one(el)
            return {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(one, el) for el in todo]
        errors = [f.exception() for f in futures if f.exception()]
        if errors:
            raise errors[0]
        return {}

    def page(s):
        parsed = load_elements(s)
        build_visual_page(visual_dir(s), parsed["elements"],
                          Path(s["project"]) / parsed["base"] / "game" / "art" / "art.js")
        update_state_md(Path(s["project"]), s, "視覺設計: 等使用者挑方案")
        return {}

    def pick(s):
        vdir = visual_dir(s)
        ans = interrupt({"kind": "waiting_visual_pick", "options_page": str(vdir / "options" / "index.html")})
        parsed = load_elements(s)
        codes = [e["code"] for e in parsed["elements"]]
        text = Path(ans["feedback"]).read_text(encoding="utf-8")
        try:
            picks = parse_visual_pick(text, codes, redo=ans["choice"] == "redo")
        except ValueError as e:
            raise LabError(str(e)) from e
        if ans["choice"] == "redo":
            opts = vdir / "options"
            for code, p in picks.items():   # 只重做列出的元素, 其他保留
                for i in OPTION_IDS:
                    (opts / f"{code}-{i}.js").unlink(missing_ok=True)
                (opts / f".done-{code}").unlink(missing_ok=True)
                (opts / f"{code}-redo.md").write_text(p["note"] or "換不同方向", encoding="utf-8")
            return Command(goto="visual_art")
        write_direction(vdir, parsed, picks)
        update_state_md(Path(s["project"]), s, "製作中", "視覺設計定案方向")
        return Command(goto=done, update={"visual_base": parsed["base"]})

    g.add_node("visual_list", list_elements)
    g.add_node("visual_confirm", confirm)
    g.add_node("visual_art", art)
    g.add_node("visual_page", page)
    g.add_node("visual_pick", pick, destinations=("visual_art", done))
    g.add_edge("visual_list", "visual_confirm")
    g.add_edge("visual_confirm", "visual_art")
    g.add_edge("visual_art", "visual_page")
    g.add_edge("visual_page", "visual_pick")
    return "visual_list"
