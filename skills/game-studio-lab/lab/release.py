"""發布階段: 把打磨定版的遊戲複製成網站版, 做圖示 / 主色 / 遊戲橫幅方案, 使用者挑完後定版。

產出 <專案>/release/: game/(網站版遊戲)、options/(方案與選擇頁)、assets/(定版素材)。
規格見 docs/2026-10-29-release-stage-design.md。
"""
import html
import json
import math
import re
import struct
import zlib
from pathlib import Path

ICON = (512, 512)
BANNER = (1680, 720)  # 網站試玩頁頂端的封面, 21:9 跟遊戲畫面同尺寸; 左下角會被遊戲圖示蓋住
ICON_IDS = ("A", "B", "C")
COLOR_IDS = ("1", "2", "3")
MAX_FILE_MB = 25
DEVICE_PC, DEVICE_MOBILE = "只支援電腦", "電腦與手機都支援"
KEEP_MD = {"audio/credits.md"}  # 免費素材的授權來源要跟著遊戲公開, 其他 .md 都是開發文件
CODE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _parse_kv(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]?\s*([^:：]+?)\s*[:：]\s*(.*?)\s*$", line)
        if m and m.group(2):
            out[m.group(1)] = m.group(2)
    return out


def parse_release_info(text: str) -> dict:
    kv = _parse_kv(text)
    missing = [k for k in ("名稱", "代號", "介紹") if not kv.get(k)]
    if missing:
        raise ValueError(f"發布資訊缺少: {'、'.join(missing)}")
    code = kv["代號"].strip("`")
    if not CODE_RE.match(code):
        raise ValueError(f"代號「{code}」格式不對: 只能用英文小寫、數字與連字號, 例 dungeon-zoo")
    return {"name": kv["名稱"], "code": code, "intro": kv["介紹"]}


def parse_release_pick(text: str) -> dict:
    kv = _parse_kv(text)
    rules = {"圖示": ("icon", ICON_IDS), "主色": ("color", COLOR_IDS), "橫幅": ("banner", ICON_IDS)}
    out = {}
    for label, (key, allowed) in rules.items():
        v = (kv.get(label) or "").strip().upper()
        if v not in allowed:
            raise ValueError(f"挑選結果的「{label}」要是 {' / '.join(allowed)} 其中一個, 實際: {v or '沒填'}")
        out[key] = v
    return out


SITE_RATIO = "21:9"  # PVD計畫網站遊玩框的比例(《遊戲接入規範》第四節), 建議尺寸 1680×720


def aspect_ratio(iface: dict) -> tuple[str, bool]:
    """回傳 (比例文字, 是否符合網站的 21:9)。1680×720 約分是 7:3, 照網站慣用寫法回 "21:9"。"""
    c = iface.get("canvas") or {}
    w, h = int(c.get("width") or 0), int(c.get("height") or 0)
    if not w or not h:
        return "未知", False
    if w * 9 == h * 21:
        return SITE_RATIO, True
    g = math.gcd(w, h)
    return f"{w // g}:{h // g}", False


def png_size(path: Path) -> tuple[int, int]:
    data = Path(path).read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} 不是 PNG")
    return struct.unpack(">II", data[16:24])


def write_png(path: Path, w: int, h: int, rgb=(255, 255, 255)) -> None:
    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))
    row = b"\x00" + bytes(rgb) * w
    raw = zlib.compress(row * h)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


_PAGE_CSS = """
body{margin:0;padding:24px;background:#f6f4f8;color:#2d2144;font-family:"Noto Sans TC","Microsoft JhengHei",sans-serif}
h1{font-size:22px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 12px}
.row{display:flex;flex-wrap:wrap;gap:24px}
.opt{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.opt h3{margin:0 0 10px;font-size:16px}
.big{display:block;max-width:100%}
.ban{position:relative;display:inline-block;max-width:100%}
.ban::after{content:"圖示會蓋住";position:absolute;left:0;bottom:0;width:25%;height:30%;box-sizing:border-box;border:2px dashed #fff;background:rgba(0,0,0,.35);color:#fff;font-size:12px;display:flex;align-items:center;justify-content:center}
.thumbs{display:flex;align-items:flex-end;gap:12px;margin-top:12px}
.thumbs img{border-radius:22%;border:4px solid #2d2144;display:block}
.card{display:flex;align-items:center;gap:12px;width:320px;padding:14px;border-radius:16px}
.card img{width:56px;height:56px;border-radius:22%;border:3px solid #2d2144}
.card b{display:block;font-size:17px}.card span{font-size:13px;opacity:.85}
.note{font-size:13px;margin-top:8px;max-width:320px}
"""


def build_options_page(release: Path, info: dict, colors: list[dict]) -> Path:
    e = html.escape
    icons = "".join(
        f'<div class="opt"><h3>圖示 {i}</h3><img class="big" src="icon-{i.lower()}.png" width="256" height="256">'
        f'<div class="thumbs">' + "".join(f'<img src="icon-{i.lower()}.png" width="{s}" height="{s}">'
                                           for s in (150, 60, 30)) + "</div></div>"
        for i in ICON_IDS)
    cards = "".join(
        f'<div class="opt"><h3>主色 {c["id"]}</h3>'
        f'<div class="card" style="background:{e(c["bg"])};color:{e(c["fg"])}">'
        f'<img src="icon-a.png"><div><b>{e(info["name"])}</b><span>{e(info.get("time", ""))}</span></div></div>'
        f'<div class="note">{e(c["bg"])} / 字 {e(c["fg"])}　{e(c.get("note", ""))}</div></div>'
        for c in colors)
    banners = "".join(f'<div class="opt"><h3>橫幅 {i}</h3><div class="ban"><img class="big" src="banner-{i.lower()}.png" width="700"></div></div>'
                      for i in ICON_IDS)
    page = (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>{e(info["name"])} 發布方案</title>'
            f"<style>{_PAGE_CSS}</style></head><body><h1>{e(info['name'])} 發布方案</h1>"
            f"<div>看完回報代號, 例「圖示 B、主色 2、橫幅 A」</div>"
            f'<h2>遊戲圖示</h2><div class="row">{icons}</div>'
            f'<h2>遊戲主色</h2><div class="row">{cards}</div>'
            f'<h2>遊戲橫幅</h2><div class="row">{banners}</div></body></html>')
    out = Path(release) / "options" / "index.html"
    out.write_text(page, encoding="utf-8")
    return out


def prune_release_game(game: Path) -> list[str]:
    """網站版只留執行時會載入的檔: 刪掉開發文件(.md, 授權來源除外)與沒被 index.html 或其他程式提到的 .js。"""
    game = Path(game)
    removed = []
    for p in sorted(game.rglob("*.md")):
        rel = p.relative_to(game).as_posix()
        if rel not in KEEP_MD:
            p.unlink(); removed.append(rel)
    scripts = sorted(game.rglob("*.js"))
    for p in scripts:
        others = [game / "index.html", *(q for q in scripts if q != p and q.exists())]
        text = "".join(q.read_text(encoding="utf-8", errors="ignore") for q in others if q.exists())
        if p.name not in text:
            p.unlink(); removed.append(p.relative_to(game).as_posix())
    return removed


def _hex6(c: str) -> str:
    c = c.strip().lower()
    return "#" + "".join(ch * 2 for ch in c[1:]) if re.fullmatch(r"#[0-9a-f]{3}", c) else c


def write_site_info(release: Path, info: dict, color: dict) -> Path:
    """給網站同步工具讀的 assets/info.json(格式見 PVD計畫網站《遊戲發布格式》第三節)。"""
    data = {"code": info["code"], "name": info["name"], "intro": info["intro"],
            "time": re.sub(r"\s*[-~～—]\s*", "–", info.get("time", ""), count=1),
            "mobile": bool(info.get("mobile")), "color": _hex6(color["bg"]),
            "textColor": "#ffffff" if _hex6(color["fg"]) == "#ffffff" else "#2d2144",
            "ratio": info.get("ratio", "未知")}
    out = Path(release) / "assets" / "info.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def write_asset_info(release: Path, info: dict, color: dict) -> Path:
    time = info.get("time", "") + ("(估計)" if info.get("time_estimated") else "")
    ratio = info.get("ratio", "未知")
    ratio_text = ratio + ("" if info.get("ratio_site") else f"(不是 {SITE_RATIO}, 網站會加邊)")
    fg = "白色字" if color["fg"].lower() in ("#fff", "#ffffff") else "深色字"
    rows = [("遊戲代號", f"`{info['code']}`"), ("遊戲名稱", info["name"]), ("遊戲圖示", "`icon.png`(512×512)"),
            ("遊戲介紹", info["intro"]), ("遊玩時長", time), ("支援裝置", DEVICE_MOBILE if info.get("mobile") else DEVICE_PC),
            ("遊戲主色", f"`{color['bg']}`, 字用{fg} `{color['fg']}`"),
            ("遊戲檔案", "`../game/`(入口 `index.html`)"), ("遊戲畫面比例", ratio_text),
            ("遊戲橫幅", "`banner.png`(1680×720)")]
    text = f"# {info['name']} 素材資訊\n\n| 項目 | 內容 |\n|---|---|\n" + "".join(f"| {k} | {v} |\n" for k, v in rows)
    out = Path(release) / "assets" / "素材資訊.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out
