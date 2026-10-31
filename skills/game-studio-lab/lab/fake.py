"""假執行器: 不呼叫 Claude, 直接寫出固定內容的檔案。測試與 LAB_FAKE_CLAUDE=1 時使用。

break_once: {(kind, game)} 該任務第一次寫出壞掉的產物(讓接合腳本抓到)
fail_once:  {(kind, game)} 該任務第一次直接拋錯(模擬 claude -p 當掉)
triage_target: 錯誤判定一律退回給誰(預設看哪個檔壞了)
"""
import json
import shutil
import threading
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "good"
STUDIO_REFS = Path(__file__).resolve().parent.parent / "references"


class FakeRunner:
    def __init__(self, break_once=None, fail_once=None, games_per_round=2, drop_option=None, touch="none"):
        self.drop_option = drop_option  # 發布美術少寫的那張繪製頁(例 "banner-c.html")
        self.touch = touch  # 發布 RD 寫進 touch.js 的 CONFIG.mode; None = 沒加觸控層
        self.break_once = set(break_once or ())
        self.fail_once = set(fail_once or ())
        self.games_per_round = games_per_round
        self.calls = []
        self._lock = threading.Lock()

    def run(self, kind: str, ctx: dict) -> str:
        key = (kind, ctx.get("game"))
        with self._lock:
            self.calls.append((kind, ctx.get("round_dir"), ctx.get("game")))
            if key in self.fail_once:
                self.fail_once.discard(key)
                raise RuntimeError(f"假的 claude 當掉: {key}")
            broken = key in self.break_once
            self.break_once.discard(key)
        getattr(self, "_" + kind.replace("-", "_"))(ctx, broken)
        return f"fake {kind} done"

    # ---- 各任務 ----
    def _design(self, ctx, broken):
        project = Path(ctx["project"])
        round_dir = project / ctx["round_dir"]
        names = ["game"] if ctx["stage"] == "polish" else \
            [f"game-{c}" for c in "abc"[: self.games_per_round]]
        for name in names:
            d = round_dir / name
            d.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(FIXTURE / "interface.json", d / "interface.json")
            (d / "spec.md").write_text(f"# {name} 規格\n", encoding="utf-8")
            if ctx["stage"] != "polish":
                (d / "guide.md").write_text(f"# {name} 說明\n", encoding="utf-8")
        with open(project / "hypotheses.md", "a", encoding="utf-8") as f:
            f.write(f"- {ctx['round_dir']} 設計: 加入假設\n")

    def _art(self, ctx, broken):
        dest = Path(ctx["game_dir"]) / "game" / "art"
        dest.mkdir(parents=True, exist_ok=True)
        text = (FIXTURE / "game" / "art" / "art.js").read_text(encoding="utf-8")
        if broken:
            text = text.replace("drawCoin(ctx, state)", "drawCoinBroken(ctx, state)")
        (dest / "art.js").write_text(text, encoding="utf-8")
        (dest / "style.md").write_text("# 風格\n", encoding="utf-8")

    _art_fix = _art

    def _rd(self, ctx, broken):
        dest = Path(ctx["game_dir"]) / "game"
        dest.mkdir(parents=True, exist_ok=True)
        html = (FIXTURE / "game" / "index.html").read_text(encoding="utf-8")
        js = (FIXTURE / "game" / "game.js").read_text(encoding="utf-8")
        if ctx["stage"] != "polish":
            html = html.replace('<script src="audio/sound.js"></script>\n', "")
            js = "\n".join(ln for ln in js.splitlines() if "Sound." not in ln)
        if broken:
            js = js.replace("const ctx =", "const ctx = notDefined +")
        (dest / "index.html").write_text(html, encoding="utf-8")
        (dest / "game.js").write_text(js, encoding="utf-8")

    _rd_fix = _rd

    def _audio(self, ctx, broken):
        dest = Path(ctx["game_dir"]) / "game" / "audio"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURE / "game" / "audio" / "sound.js", dest / "sound.js")
        (dest / "sound.md").write_text("# 音效\n", encoding="utf-8")
        (dest / "credits.md").write_text("# 授權\n", encoding="utf-8")

    _audio_fix = _audio

    def _triage(self, ctx, broken):
        report = json.loads(Path(ctx["report"]).read_text(encoding="utf-8"))
        if "art" in {e["step"] for e in report["errors"]}:
            targets = {"art": "補上介面上的函式"}
        else:
            targets = {"rd": "修正 game.js 的錯誤"}
        Path(ctx["out"]).write_text(json.dumps({"targets": targets}, ensure_ascii=False), encoding="utf-8")

    def _bugfix(self, ctx, broken):
        p = Path(ctx["game_dir"]) / "game" / "game.js"
        p.write_text(p.read_text(encoding="utf-8") + "\n// bug fixed\n", encoding="utf-8")

    def _review(self, ctx, broken):
        with open(Path(ctx["project"]) / "hypotheses.md", "a", encoding="utf-8") as f:
            f.write(f"- {ctx['round_dir']} 檢討: 選擇 {ctx['choice']}\n")

    # ---- 發布 ----
    def _release_game(self, ctx, broken):
        release = Path(ctx["release_dir"])
        p = release / "game" / "game.js"
        p.write_text(p.read_text(encoding="utf-8") + "\n// release\n", encoding="utf-8")
        if self.touch:  # 照發布任務: 範本複製成 touch.js、改 CONFIG.mode、index.html 在 game.js 之後載入
            tpl = (STUDIO_REFS / "touch-template.js").read_text(encoding="utf-8")
            (release / "game" / "touch.js").write_text(tpl.replace("mode: 'keys',", f"mode: '{self.touch}',", 1), encoding="utf-8")
            idx = release / "game" / "index.html"
            idx.write_text(idx.read_text(encoding="utf-8").replace(
                '<script src="game.js"></script>', '<script src="game.js"></script>\n<script src="touch.js"></script>'), encoding="utf-8")
        if not (release / "interface.json").exists():
            shutil.copyfile(FIXTURE / "interface.json", release / "interface.json")

    def _release_info(self, ctx, broken):
        out = Path(ctx["release_dir"]) / "options" / "info.json"
        out.write_text(json.dumps({"time": "5–10 分鐘", "time_estimated": True},
                                  ensure_ascii=False), encoding="utf-8")

    def _release_art(self, ctx, broken):
        opts = Path(ctx["release_dir"]) / "options"
        for n in ("icon-a", "icon-b", "icon-c", "banner-a", "banner-b", "banner-c"):
            if f"{n}.html" != self.drop_option:
                (opts / f"{n}.html").write_text(f"<!doctype html><title>{n}</title>", encoding="utf-8")
        colors = [{"id": str(i), "bg": bg, "fg": "#2d2144", "note": "假"}
                  for i, bg in enumerate(("#f29cac", "#aaefd5", "#e0c64f"), 1)]
        (opts / "colors.json").write_text(json.dumps(colors), encoding="utf-8")
