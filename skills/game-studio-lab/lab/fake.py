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


class FakeRunner:
    def __init__(self, break_once=None, fail_once=None, games_per_round=2):
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
