"""發布子圖: 遊戲複本 → 素材資訊 → 美術方案 → 輸出 PNG + 選擇頁 → 等使用者挑選 → 定版。

打磨停點選 release 時掛在主圖底下跑; 非 lab 專案(例: 捕泡手)由 `lab release` 指令單獨編譯。
只有 pick 會停下來等人(interrupt)。
"""
import json
import shutil
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from lab.graph import LabError
from lab.release import (ICON, ICON_IDS, MAX_FILE_MB, SHARE, aspect_ratio, build_options_page, detect_mobile,
                         parse_release_info, parse_release_pick, png_size, prune_release_game, write_asset_info,
                         write_site_info)
from lab.renderer import ChromeRenderer


class ReleaseState(TypedDict, total=False):
    project: str
    round_dir: str
    feedback: str        # 發布資訊檔(名稱 / 代號 / 介紹)
    standalone: bool     # True: 非 lab 專案, 遊戲在 <project>/game/
    pick: dict           # 使用者挑的方案 {"icon", "color", "share"}
    release_warnings: list


class ReleaseOutput(TypedDict):
    release_warnings: list


OPTION_PAGES = [f"icon-{i.lower()}" for i in ICON_IDS] + [f"share-{i.lower()}" for i in ICON_IDS]


def build_release_graph(deps, checkpointer=None):
    renderer = getattr(deps, "renderer", None) or ChromeRenderer()

    def paths(s):
        project = Path(s["project"])
        src = project if s.get("standalone") else project / s["round_dir"] / "game"
        return project, src, project / "release"

    def ctx(s) -> dict:
        project, src, release = paths(s)
        info = parse_release_info(Path(s["feedback"]).read_text(encoding="utf-8"))
        logs = project / "telemetry.md" if s.get("standalone") else project / "polish" / "logs"
        return {"project": str(project), "stage": "release", "release_dir": str(release), "src_dir": str(src),
                "logs": str(logs), **info}

    def game(s: ReleaseState):
        project, src, release = paths(s)
        if (release / "game").exists():
            shutil.rmtree(release / "game")
        release.mkdir(parents=True, exist_ok=True)
        (release / "options" / "redo-notes.md").unlink(missing_ok=True)  # 上一次發布的重做意見不沿用
        shutil.copytree(src / "game", release / "game")
        if (src / "interface.json").exists():
            shutil.copyfile(src / "interface.json", release / "interface.json")
        deps.runner.run("release-game", ctx(s))
        prune_release_game(release / "game")
        targets = [release / "game"] + ([] if s.get("standalone") else [src / "game"])
        for t in targets:
            result = deps.checker.check(t, "polish")
            if not result["ok"]:
                raise LabError(f"{t.relative_to(project)} 發布修改後接合腳本不過: {result['errors']}")
        return {"release_warnings": []}

    def info(s: ReleaseState):
        _, _, release = paths(s)
        (release / "options").mkdir(parents=True, exist_ok=True)
        out = release / "options" / "info.json"
        out.unlink(missing_ok=True)
        c = ctx(s)
        deps.runner.run("release-info", c)
        if not out.exists():
            raise LabError("素材資訊節點沒有寫出 release/options/info.json")
        data = json.loads(out.read_text(encoding="utf-8"))
        iface_path = release / "interface.json"
        iface = json.loads(iface_path.read_text(encoding="utf-8")) if iface_path.exists() else {}
        ratio, is_16_9 = aspect_ratio(iface)
        data.update({k: c[k] for k in ("name", "code", "intro")})
        data.update({"ratio": ratio, "ratio_16_9": is_16_9, "mobile": detect_mobile(release / "game")})
        out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return {}

    def art(s: ReleaseState):
        _, _, release = paths(s)
        opts = release / "options"
        for p in [*opts.glob("icon-*"), *opts.glob("share-*"), opts / "colors.json"]:
            p.unlink(missing_ok=True)
        deps.runner.run("release-art", ctx(s))
        missing = [f"{n}.html" for n in OPTION_PAGES if not (opts / f"{n}.html").exists()]
        if not (opts / "colors.json").exists():
            missing.append("colors.json")
        if missing:
            raise LabError(f"美術方案缺檔: {', '.join(missing)}")
        colors = json.loads((opts / "colors.json").read_text(encoding="utf-8"))
        if sorted(str(c.get("id")) for c in colors) != ["1", "2", "3"]:
            raise LabError(f"colors.json 應有 id 1~3 三組主色, 實際: {colors}")
        return {}

    def render(s: ReleaseState):
        _, _, release = paths(s)
        opts = release / "options"
        for n in OPTION_PAGES:
            size = ICON if n.startswith("icon") else SHARE
            out = opts / f"{n}.png"
            renderer.render(opts / f"{n}.html", out, size)
            if png_size(out) != size:
                raise LabError(f"{n}.png 尺寸是 {png_size(out)}, 應為 {size}")
        build_options_page(release, json.loads((opts / "info.json").read_text(encoding="utf-8")),
                           json.loads((opts / "colors.json").read_text(encoding="utf-8")))
        return {}

    def pick(s: ReleaseState):
        _, _, release = paths(s)
        ans = interrupt({"kind": "waiting_release_pick",
                         "options_page": str(release / "options" / "index.html")})
        if ans["choice"] == "redo":
            return Command(goto="art")
        try:
            chosen = parse_release_pick(Path(ans["feedback"]).read_text(encoding="utf-8"))
        except ValueError as e:
            raise LabError(str(e)) from e
        return Command(goto="finalize", update={"pick": chosen})

    def finalize(s: ReleaseState):
        _, _, release = paths(s)
        opts, assets = release / "options", release / "assets"
        chosen = s["pick"]
        if assets.exists():
            shutil.rmtree(assets)
        assets.mkdir()
        shutil.copyfile(opts / f"icon-{chosen['icon'].lower()}.png", assets / "icon.png")
        shutil.copyfile(opts / f"share-{chosen['share'].lower()}.png", assets / "share.png")
        info_data = json.loads((opts / "info.json").read_text(encoding="utf-8"))
        colors = json.loads((opts / "colors.json").read_text(encoding="utf-8"))
        color = next(c for c in colors if str(c["id"]) == chosen["color"])
        write_asset_info(release, info_data, color)
        write_site_info(release, info_data, color)
        warnings = [f"{p.relative_to(release)} 有 {p.stat().st_size / 1024 / 1024:.1f}MB, 超過網站上限 {MAX_FILE_MB}MB"
                    for d in (release / "game", assets) for p in d.rglob("*")
                    if p.is_file() and p.stat().st_size > MAX_FILE_MB * 1024 * 1024]
        return {"release_warnings": warnings}

    g = StateGraph(ReleaseState, output_schema=ReleaseOutput)
    for name, fn in [("game", game), ("info", info), ("art", art), ("render", render), ("pick", pick),
                     ("finalize", finalize)]:
        g.add_node(name, fn)
    g.add_edge(START, "game")
    g.add_edge("game", "info")
    g.add_edge("info", "art")
    g.add_edge("art", "render")
    g.add_edge("render", "pick")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)
