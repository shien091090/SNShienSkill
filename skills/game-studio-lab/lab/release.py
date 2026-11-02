"""發布階段: 把打磨定版的遊戲複製成網站版, 做圖示 / 主色(含色帶圖樣) / 遊戲橫幅方案, 使用者挑完後定版。

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

from lab.loader import loader_files

ICON = (512, 512)
BANNER = (1680, 720)  # 網站遊戲清單(電腦與手機)的選擇按鈕(21:9); 左下角會疊時長標籤
PATTERN = (256, 256)  # 試玩頁頂端主題色帶的圖塊, 網站以 128×128 重複鋪滿
ICON_IDS = ("A", "B", "C")
COLOR_IDS = ("1", "2", "3")
MAX_FILE_MB = 25
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


SITE_RATIO = "16:9"  # PVD計畫網站電腦遊玩框的比例, 遊戲設計寬 1280×720; 手機全螢幕, 寬度依螢幕最寬到 MAX_W
MAX_W = 1680  # 手機最寬 21:9


def _ratio_text(w: int, h: int) -> str:
    if w * 9 == h * 21:
        return "21:9"  # 1680×720 約分是 7:3, 照網站慣用寫法
    g = math.gcd(w, h)
    return f"{w // g}:{h // g}"


def aspect_ratio(iface: dict) -> tuple[str, bool, str]:
    """回傳 (電腦比例, 是否符合網站的 16:9, 手機比例)。
    介面 canvas 的 width 是設計寬(電腦用這個寬), maxWidth 是觸控裝置最寬; 手機比例例 "16:9-21:9"。"""
    c = iface.get("canvas") or {}
    w, h = int(c.get("width") or 0), int(c.get("height") or 0)
    if not w or not h:
        return "未知", False, "未知"
    max_w = int(c.get("maxWidth") or w)
    ratio = _ratio_text(w, h)
    mobile = ratio if max_w <= w else f"{ratio}-{_ratio_text(max_w, h)}"
    return ratio, ratio == SITE_RATIO and w <= max_w <= MAX_W * h // 720, mobile


def png_size(path: Path) -> tuple[int, int]:
    data = Path(path).read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} 不是 PNG")
    return struct.unpack(">II", data[16:24])


def png_pixels(path: Path) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    """讀 8 位元、不交錯的 RGB / RGBA PNG(Chrome 截圖就是這種), 回傳 (寬, 高, 每點 RGBA)。"""
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} 不是 PNG")
    pos, idat, hdr = 8, b"", None
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        tag, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        if tag == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat += body
        pos += 12 + n
    w, h, depth, ctype, _, _, interlace = hdr
    if depth != 8 or ctype not in (2, 6) or interlace:
        raise ValueError(f"{path} 不是 8 位元不交錯的 RGB / RGBA PNG")
    bpp = 3 if ctype == 2 else 4
    raw, stride, prev, px = zlib.decompress(idat), w * bpp, bytearray(w * bpp), []
    for y in range(h):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b, c = prev[i], prev[i - bpp] if i >= bpp else 0
            if f == 1: line[i] = (line[i] + a) & 255
            elif f == 2: line[i] = (line[i] + b) & 255
            elif f == 3: line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c; pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        px += [(line[i], line[i + 1], line[i + 2], line[i + 3] if bpp == 4 else 255) for i in range(0, stride, bpp)]
        prev = line
    return w, h, px


def pattern_problems(path: Path, bg: str) -> list[str]:
    """檢查色帶圖樣是否符合網站規格: 尺寸、不透明、底色是主色、紋路淡、四邊接得起來。回傳問題清單。"""
    w, h, px = png_pixels(path)
    if (w, h) != PATTERN:
        return [f"尺寸是 {w}×{h}, 應為 {PATTERN[0]}×{PATTERN[1]}"]
    out = []
    if any(p[3] < 255 for p in px):
        out.append("有透明的地方, 要整張不透明")
    c = _hex6(bg)
    want = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    def dist(p, q=want): return max(abs(p[k] - q[k]) for k in range(3))
    common = max(set(px), key=px.count)
    if dist(common) > 24:  # 底色允許一點色差(Chrome 截圖的色彩轉換), 超過就是換了底色
        out.append(f"底色 {'#%02x%02x%02x' % common[:3]} 不是主色 {c}")
    if sum(1 for p in px if dist(p, common) > 72) > len(px) * 0.02:  # 紋路要淡: 和底色差很多的點不超過 2%
        out.append("紋路對比太高, 要淡、對比低")
    def seam(a, b): return sum(dist(a[i], b[i]) for i in range(len(a))) / len(a)
    col = lambda x: [px[y * w + x] for y in range(h)]
    row = lambda y: px[y * w:(y + 1) * w]
    inner = max(seam(col(w // 2 - 1), col(w // 2)), seam(row(h // 2 - 1), row(h // 2)), 1)
    if seam(col(w - 1), col(0)) > inner * 3 + 4 or seam(row(h - 1), row(0)) > inner * 3 + 4:  # 接縫處的落差明顯大於圖中間 = 拼起來看得到線
        out.append("左右或上下邊緣接不起來, 重複鋪滿時會看到接縫")
    return out


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
.ban::after{content:"時長標籤";position:absolute;left:0;bottom:0;width:30%;height:25%;box-sizing:border-box;border:2px dashed #fff;background:rgba(0,0,0,.35);color:#fff;font-size:12px;display:flex;align-items:center;justify-content:center}
.thumbs{display:flex;align-items:flex-end;gap:12px;margin-top:12px}
.thumbs img{border-radius:22%;border:4px solid #2d2144;display:block}
.band{width:500px;max-width:100%;height:76px;border-radius:12px 12px 0 0;background-size:128px 128px}
.card{position:relative;width:500px;max-width:100%;background:#fff;border-radius:0 0 12px 12px;padding:34px 16px 12px;box-sizing:border-box}
.card img{position:absolute;left:16px;top:-40px;width:64px;height:64px;border-radius:22%;border:3px solid #2d2144}
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
        f'<div class="band" style="background-color:{e(c["bg"])};background-image:url(pattern-{e(str(c["id"]))}.png)"></div>'
        f'<div class="card"><img src="icon-a.png"><b>{e(info["name"])}</b><span>{e(info.get("time", ""))}</span></div>'
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


# PVD計畫網站《遊戲接入規範》: 儲存鍵名「<代號>:<用途>」、不清空共用儲存、不動上層頁面(第一、四節)
STORAGE_KEY_RE = re.compile(r"""\b(?:localStorage|sessionStorage)\.(?:getItem|setItem|removeItem)\(\s*(['"`])([^'"`]*)\1""")
SITE_FORBIDDEN = [(re.compile(r"\b(?:localStorage|sessionStorage)\.clear\s*\("), "清空整個共用儲存空間"),
                  (re.compile(r"\bwindow\.top\b|\btop\.location\b|\bparent\.location\b"), "碰上層頁面"),
                  (re.compile(r"\bwindow\.open\s*\("), "開新視窗"),
                  (re.compile(r"\blocation\.(?:href\s*=(?!=)|assign\s*\(|replace\s*\(|reload\s*\()"), "改網址或重新載入")]


def site_rule_warnings(game: Path, code: str) -> list[str]:
    """掃網站版程式, 列出違反接入規範的寫法(只抓字面上看得出來的; 動態組出的鍵名靠 RD 自測)。"""
    game = Path(game)
    out = []
    for p in sorted([*game.rglob("*.js"), *game.rglob("*.html")]):
        rel = p.relative_to(game).as_posix()
        text = p.read_text(encoding="utf-8", errors="ignore")
        for m in STORAGE_KEY_RE.finditer(text):
            key = m.group(2)
            if not key.startswith(f"{code}:"):
                out.append(f"{rel} 的儲存鍵名「{key}」不是「{code}:用途」格式")
        for rx, what in SITE_FORBIDDEN:
            if rx.search(text):
                out.append(f"{rel} 有{what}的寫法(接入規範不允許)")
    return list(dict.fromkeys(out))


TOUCH_MODE_RE = re.compile(r"""\bmode:\s*['"](keys|mouse|none)['"]""")


def touch_mode(game: Path) -> str | None:
    """網站版遊戲的觸控層設定(touch.js 的 CONFIG.mode); 沒有 touch.js 或 index.html 沒載入它 → None。"""
    game = Path(game)
    touch, index = game / "touch.js", game / "index.html"
    if not touch.exists() or not index.exists() or not any(re.fullmatch(r"(\./)?touch\.js", f) for f in loader_files(index.read_text(encoding="utf-8"))):
        return None
    m = TOUCH_MODE_RE.search(touch.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def _hex6(c: str) -> str:
    c = c.strip().lower()
    return "#" + "".join(ch * 2 for ch in c[1:]) if re.fullmatch(r"#[0-9a-f]{3}", c) else c


def write_site_info(release: Path, info: dict, color: dict) -> Path:
    """給網站同步工具讀的 assets/info.json(格式見 PVD計畫網站《遊戲發布格式》第三節)。"""
    data = {"code": info["code"], "name": info["name"], "intro": info["intro"],
            "time": re.sub(r"\s*[-~～—]\s*", "–", info.get("time", ""), count=1),
            "color": _hex6(color["bg"]),
            "textColor": "#ffffff" if _hex6(color["fg"]) == "#ffffff" else "#2d2144",
            "ratio": info.get("ratio", "未知")}
    data["mobileRatio"] = info.get("mobile_ratio") or data["ratio"]
    out = Path(release) / "assets" / "info.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def write_asset_info(release: Path, info: dict, color: dict) -> Path:
    time = info.get("time", "") + ("(估計)" if info.get("time_estimated") else "")
    ratio = info.get("ratio", "未知")
    ratio_text = ratio + ("" if info.get("ratio_site") else f"(不是 {SITE_RATIO}, 網站會加邊)")
    if info.get("mobile_ratio") and info["mobile_ratio"] != ratio:
        ratio_text = f"電腦 {ratio_text}; 手機依螢幕 {info['mobile_ratio'].replace('-', '～')}"
    fg = "白色字" if color["fg"].lower() in ("#fff", "#ffffff") else "深色字"
    rows = [("遊戲代號", f"`{info['code']}`"), ("遊戲名稱", info["name"]), ("遊戲圖示", "`icon.png`(512×512)"),
            ("遊戲介紹", info["intro"]), ("遊玩時長", time),
            ("遊戲主色", f"`{color['bg']}`, 字用{fg} `{color['fg']}`"),
            ("遊戲檔案", "`../game/`(入口 `index.html`)"), ("遊戲畫面比例", ratio_text),
            ("遊戲橫幅", "`banner.png`(1680×720)"), ("色帶圖樣", "`pattern.png`(256×256, 跟主色一組)")]
    text = f"# {info['name']} 素材資訊\n\n| 項目 | 內容 |\n|---|---|\n" + "".join(f"| {k} | {v} |\n" for k, v in rows)
    out = Path(release) / "assets" / "素材資訊.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out
