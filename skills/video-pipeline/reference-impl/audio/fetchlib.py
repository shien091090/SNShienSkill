"""Gather candidate sounds from free libraries into lib/<source>/ with a catalog.

sources (all usable commercially without credit; see lib/CREDITS.md):
  mixkit   - Mixkit Sound Effects Free License (category pages, preview mp3)
  lab      - 効果音ラボ soundeffect-lab.info (category pages, mp3)
  ov       - Openverse API, CC0 only (mostly Freesound HQ previews)
usage: python fetchlib.py            -> lib/catalog.json (+ downloads)
       python fetchlib.py --music    -> lib/music.json + lib/music/*.mp3 (Mixkit stock music)
"""
import html, json, pathlib, re, sys, time, urllib.parse, urllib.request

HERE = pathlib.Path(__file__).parent
LIB = HERE / "lib"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get(url, binary=False, ref=None):
    req = urllib.request.Request(url, headers={**UA, **({"Referer": ref} if ref else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        b = r.read()
    return b if binary else b.decode("utf-8", "replace")


def save(url, path, ref=None):
    if path.exists() and path.stat().st_size > 0:
        return True
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(get(url, True, ref))
        return True
    except Exception as e:
        print("  fail", url, e)
        return False


MIXKIT = ["whoosh", "transition", "pop", "click", "game", "cartoon", "impact", "sword", "magic", "bell",
          "coin", "glass", "hit", "swoosh", "bubble", "jump", "fall", "stamp", "metal", "wood", "punch",
          "notification", "interface", "shimmer", "sparkle", "achievement", "paper", "slide"]
LAB = ["anime", "battle", "machine", "button", "various"]
OV = ["whoosh", "swoosh soft", "pop", "cartoon pop", "stamp", "rubber stamp", "coin", "coin pickup",
      "sword unsheathe", "sword slash", "glass break", "glass crack", "sparkle", "chime", "bell ding",
      "box close", "lid close", "wood impact", "thud", "click", "pluck", "bubble pop", "jump", "magic",
      "transition", "poker chips", "paper slide", "gear", "ratchet", "boing"]


def mixkit(cat):
    out = []
    try:
        s = get(f"https://mixkit.co/free-sound-effects/{cat}/")
    except Exception as e:
        print("  mixkit", cat, e)
        return out
    for m in re.finditer(r'preview-url-value="(https://assets\.mixkit\.co/active_storage/sfx/(\d+)/\d+-preview\.mp3)"'
                         r'.*?item-grid-card__title">\s*(.*?)\s*</h2>.*?data-test-id="duration">\s*([\d:]+)', s, re.S):
        url, sid, name, dur = m.groups()
        out.append({"src": "mixkit", "id": sid, "name": html.unescape(name).strip(), "dur": dur, "url": url,
                    "file": f"mixkit/{sid}.mp3", "tag": cat})
    return out


MUSIC = ["video-game", "happy", "upbeat", "playful", "funny", "fun", "energetic", "children", "cartoon", "quirky", "positive", "corporate"]


def mixkit_music(tag):
    # Mixkit Stock Music Free License: full tracks, commercial use, no attribution
    out = []
    try:
        s = get(f"https://mixkit.co/free-stock-music/tag/{tag}/")
    except Exception as e:
        print("  music", tag, e)
        return out
    for m in re.finditer(r'preview-url-value="(https://assets\.mixkit\.co/music/(\d+)/\d+\.mp3)"'
                         r'.*?item-grid-card__title">\s*(.*?)\s*</h2>.*?music-preview__author">\s*by (.*?)\s*</p>', s, re.S):
        url, mid, name, by = m.groups()
        out.append({"src": "music", "id": mid, "name": html.unescape(name).strip(), "by": html.unescape(by).strip(),
                    "url": url, "file": f"music/{mid}.mp3", "tag": tag})
    return out


def lab(cat):
    out = []
    base = f"https://soundeffect-lab.info/sound/{cat}/"
    try:
        t = get(base)
    except Exception as e:
        print("  lab", cat, e)
        return out
    # each sound: <li><span>name</span>description<a href="x.mp3">
    for m in re.finditer(r'<li><span>(.*?)</span>(.*?)<a href="([^"]+\.mp3)"', t):
        name, desc, href = m.groups()
        url = urllib.parse.urljoin(base, href)
        fn = cat + "_" + url.rsplit("/", 1)[-1]
        out.append({"src": "lab", "id": fn, "name": html.unescape(name).strip(), "desc": html.unescape(desc).strip(),
                    "url": url, "file": f"lab/{fn}", "tag": cat, "ref": base})
    return out


def ov(q):
    out = []
    u = "https://api.openverse.org/v1/audio/?" + urllib.parse.urlencode({"q": q, "license": "cc0", "page_size": 12})
    try:
        d = json.loads(get(u))
    except Exception as e:
        print("  ov", q, e)
        return out
    for r in d.get("results", []):
        if (r.get("duration") or 0) > 6000 or r.get("filetype") not in ("mp3", "ogg", "wav"):
            continue
        out.append({"src": "ov", "id": r["id"], "name": r["title"], "dur": round((r.get("duration") or 0) / 1000, 2),
                    "url": r["url"], "file": f"ov/{r['id']}.{r['filetype']}", "tag": q, "by": r.get("creator"),
                    "page": r.get("foreign_landing_url")})
    time.sleep(0.5)
    return out


def music():
    cat = []
    for t in MUSIC:
        cat += mixkit_music(t)
    uniq = {}
    for it in cat:
        uniq.setdefault(it["file"], it)
    ok = [it for it in uniq.values() if save(it["url"], LIB / it["file"])]
    (LIB / "music.json").write_text(json.dumps(ok, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(ok), "tracks")


def main():
    cat = []
    for c in MIXKIT:
        cat += mixkit(c)
    for c in LAB:
        cat += lab(c)
    for q in OV:
        cat += ov(q)
    uniq = {}
    for it in cat:
        uniq.setdefault(it["file"], it)
    cat = list(uniq.values())
    ok = [it for it in cat if save(it["url"], LIB / it["file"], it.get("ref"))]
    (LIB / "catalog.json").write_text(json.dumps(ok, ensure_ascii=False, indent=1), encoding="utf-8")
    by = {}
    for it in ok:
        by[it["src"]] = by.get(it["src"], 0) + 1
    print(len(ok), by)


if __name__ == "__main__":
    music() if "--music" in sys.argv else main()
