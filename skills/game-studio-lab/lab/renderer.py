"""把繪製頁存成 PNG。只由程式(發布的 render 節點)啟動 Chrome, AI 節點仍禁止開瀏覽器。

繪製頁只載入 art.js, 不載入音效, 不會有殘留行程在背景播音樂的問題。
"""
import os
import subprocess
import tempfile
from pathlib import Path

from lab.release import write_png

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


class RenderError(Exception):
    pass


def find_chrome() -> str | None:
    for p in [os.environ.get("LAB_CHROME"), *CHROME_CANDIDATES]:
        if p and Path(p).exists():
            return p
    return None


class ChromeRenderer:
    def render(self, html: Path, out: Path, size: tuple[int, int]) -> None:
        chrome = find_chrome()
        if not chrome:
            raise RenderError("找不到 Chrome / Edge, 無法把方案存成 PNG(可用環境變數 LAB_CHROME 指定路徑)")
        out = Path(out).resolve()
        out.unlink(missing_ok=True)
        w, h = size
        # 獨立的設定檔資料夾: 不跟使用者開著的 Chrome 搶同一個 profile
        with tempfile.TemporaryDirectory() as profile:
            cmd = [chrome, "--headless=new", f"--user-data-dir={profile}", "--disable-gpu", "--hide-scrollbars",
                   "--mute-audio", "--no-first-run", "--no-default-browser-check", "--force-device-scale-factor=1",
                   "--allow-file-access-from-files", f"--window-size={w},{h}", "--virtual-time-budget=3000",
                   f"--screenshot={out}", Path(html).resolve().as_uri()]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   timeout=60)
            except subprocess.TimeoutExpired as e:
                raise RenderError(f"{Path(html).name} 輸出 PNG 逾時") from e
        if not out.exists():
            raise RenderError(f"{Path(html).name} 沒有輸出 PNG: {r.stderr.strip()[-500:]}")


class FakeRenderer:
    def __init__(self, wrong_size: str | None = None):
        self.wrong_size = wrong_size

    def render(self, html: Path, out: Path, size: tuple[int, int]) -> None:
        w, h = size
        if self.wrong_size and Path(html).stem == self.wrong_size:
            w, h = w + 1, h
        write_png(out, w, h)
