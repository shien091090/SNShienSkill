"""接合腳本的 Python 端: 呼叫 check/check.js 檢查一款遊戲。"""
import json
import subprocess
from pathlib import Path

CHECK_JS = Path(__file__).resolve().parent.parent / "check" / "check.js"


class NodeChecker:
    def check(self, game_dir: Path, stage: str) -> dict:
        r = subprocess.run(["node", str(CHECK_JS), str(game_dir), stage], capture_output=True,
                           text=True, encoding="utf-8", timeout=120)
        lines = [ln for ln in r.stdout.strip().splitlines() if ln.strip()]
        try:
            return json.loads(lines[-1])
        except (IndexError, json.JSONDecodeError):
            return {"ok": False, "errors": [{"step": "runner",
                                             "message": f"接合腳本沒有輸出結果: {r.stderr.strip()[-800:]}"}]}
