"""Music bed under the finished effects track (Mixkit stock music, lib/music/).

One track fades in as the PVD letters spread into words and plays on through the Develop glass
shatter until it fades out over the 3D "更有故事性" swing; after that the film has no music.
(The excerpt is still picked for the stretch up to the shatter, the part the user chose it by.)
A short melodic sting closes the film, from the "獻給一同參與開發的你們" line to the last frame. For each candidate track, beat tracking picks the excerpt:
music one gets its steadiest loud stretch starting on a downbeat, music two its strongest downbeat.
usage: python music.py --options   -> live/sfx/mus*-*.wav + live/sfxopts.js (with the effects mix as the base track)
       python music.py             -> out/final.wav: effects mix + music.json picks (+ tune.json levels)
"""
import json, pathlib, sys
import numpy as np, soundfile as sf, pyloudnorm as pyln, librosa
from scipy.signal import resample_poly
import libmix

HERE = pathlib.Path(__file__).parent
SR = libmix.SR
at, TOTAL = libmix.cue_times()
SPREAD = at["spread@98"]               # letters spread into words
SHATTER = at["shards@1178"] - 0.45     # shards start falling (the cue sits 0.45 s into the fall)
SWING = at["3d-swing@1464"]            # 3D swing into 更有故事性
GIFT = at["gift:text@1747"]            # 獻給一同參與開發的你們
TILES = at["tile:3@217"] - 0.056        # Play shrinks to the corner and the first of the 8 mini-games pops in (the cue sits 0.056 s after)
# where a track's main theme comes in after its intake-of-breath swell (track seconds, by ear and RMS);
# that entry is put on TILES, so the breath plays over Play filling the screen
THEME = {"15": 76.42}
FADE_IN, FADE_OUT = 1.5, 1.2
END_LEVEL = -22.0  # the closing sting sits just under the box and lid hits it plays across
LEVEL = -24.0  # bed loudness (LUFS over its own span): under the effects, which master at -18 with sparse hits

# (option key, label, mixkit id)
CUES = {
    "mus1": ("音樂(單字展開→故事性轉場)", SPREAD, SWING + FADE_OUT, [
        ("d", "微笑小品 Keep Smiling", "15"),
        ("a", "歡樂時光 Fun Times", "7"),
        ("b", "遊樂場 Playground Fun", "12"),
        ("c", "俏皮 Playful", "10"),
        ("e", "盪鞦韆溜滑梯 Swings and Slides", "14"),
        ("f", "杯子蛋糕 Cupcakes", "1057"),
    ]),
    "end": ("收尾音效(獻給…→結束)", GIFT, TOTAL, [
        ("a", "遊戲過關 Game level completed", "mk/2059"),
        ("b", "笛子小旋律 Melodical flute", "mk/2310"),
        ("c", "歡樂魔法小旋律 Magic festive melody", "mk/2986"),
        ("d", "節慶小旋律 Festive melody", "mk/2985"),
        ("e", "成就達成 Achievement completed", "mk/2068"),
        ("f", "豎琴輕掃 Relaxing harp sweep", "mk/2628"),
    ]),
}


def track(mid):
    x, sr = sf.read(HERE / "lib" / "music" / f"{mid}.mp3", always_2d=True)
    x = x.mean(1)
    return resample_poly(x, SR, sr) if sr != SR else x


def excerpt(x, length, kind, need=None):
    """start time of the excerpt: a downbeat (every 4th tracked beat) chosen by loudness over `length` seconds;
    `need` seconds must fit before the track ends."""
    need = need or length
    y = librosa.resample(x, orig_sr=SR, target_sr=22050)
    tempo, beats = librosa.beat.beat_track(y=y, sr=22050, units="time")
    onset = librosa.onset.onset_strength(y=y, sr=22050)
    rms = librosa.feature.rms(y=y)[0]
    fr = lambda t: min(len(rms) - 1, int(t * 22050 / 512))
    best, score = 0.0, -1e9
    for k in range(0, len(beats), 4):
        for off in range(4):  # the downbeat phase is unknown, so every beat may start a bar
            if k + off >= len(beats):
                break
            s = beats[k + off]
            if s < 4.0 or s + need > len(x) / SR - 2:  # skip intros and the ending
                continue
            seg = rms[fr(s):fr(s + length)]
            if kind == "steady":
                sc = seg.mean() - 1.5 * seg.std()
            else:  # a hit right on the start, and energy to carry it
                sc = onset[fr(s)] / (onset.mean() + 1e-9) * 0.02 + seg.mean()
            if sc > score:
                best, score = s, sc
    return best, float(np.atleast_1d(tempo)[0])


def sting(name, t0, t1):
    """a library sting from its first sound, cut to fit before the film ends."""
    y = libmix.load(name, {"len": t1 - t0 - 0.05})
    f = int(0.25 * SR); y[-f:] *= np.linspace(1, 0, f) ** 2
    m = pyln.Meter(SR)
    y = y * 10 ** ((END_LEVEL - m.integrated_loudness(np.stack([y, y], 1))) / 20)
    return y, t0, 0.0, 0.0


def clip(mid, key):
    """the cue's music, at its final level, from its own start time."""
    _, t0, t1, _ = CUES[key]
    if key == "end":
        return sting(mid, t0, t1)
    x = track(mid)
    length = t1 - t0
    s, bpm = excerpt(x, SHATTER - SPREAD, "steady", length)
    if key == "mus1" and mid in THEME:
        s = THEME[mid] - (TILES - t0)
    i = max(0, int((s - 0.01) * SR))
    y = x[i:i + int(length * SR)].copy()
    n = len(y)
    f = int(FADE_IN * SR); y[:f] *= np.sin(np.linspace(0, np.pi / 2, f)) ** 2
    f = int(FADE_OUT * SR); y[-f:] *= np.cos(np.linspace(0, np.pi / 2, f)) ** 2
    body = y[int(FADE_IN * SR):n - f]
    m = pyln.Meter(SR)
    y = y * 10 ** ((LEVEL - m.integrated_loudness(np.stack([body, body], 1))) / 20)
    return y, t0, s, bpm


def export_options():
    od = HERE.parent / "live" / "sfx"
    for f in list(od.glob("*.wav")) + list(od.glob("*.mp3")):
        f.unlink()
    # the finished effects mix (libmix.py from picks.json + tune.json) is the page's base track
    # (wav, not mp3: an mp3's encoder delay would put every effect a few ms late)
    fx, _ = sf.read(HERE / "out" / "sfx-lib.wav", always_2d=True)
    sf.write(od / "base.wav", fx.mean(1), SR, subtype="PCM_16")
    rows = []
    for key, (label, t0, t1, opts) in CUES.items():
        ro = {"id": key, "label": label, "opts": []}
        for k, name, mid in opts:
            y, t, s, bpm = clip(mid, key)
            fn = f"{key}-{k}.wav"
            sf.write(od / fn, libmix.limit(y[:, None], ceil=0.89)[:, 0], SR, subtype="PCM_16")
            ro["opts"].append({"key": k, "label": name, "clips": [{"t": round(t, 4), "src": f"sfx/{fn}"}]})
            print(f"{key} {k} {name}: from {s:.2f}s, {bpm:.0f} BPM, {len(y)/SR:.2f}s")
        ro["opts"].append({"key": "x", "label": "不要音樂", "clips": []})
        rows.append(ro)
    js = ("// music cues and their options, written by audio/music.py --options; the finished effects mix plays underneath\n"
          "window.VID_DOC = \"music\";\n"
          "window.VID_BASE = { t: 0, src: \"sfx/base.wav\" };\nwindow.VID_SFX = " + json.dumps(rows, ensure_ascii=False) + ";\n")
    (HERE.parent / "live" / "sfxopts.js").write_text(js, encoding="utf-8")


def render():
    fx, _ = sf.read(HERE / "out" / "sfx-lib.wav", always_2d=True)
    fx = fx.mean(1)
    pf, tf = HERE / "music.json", HERE / "tune.json"
    picks = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else {}
    tune = json.loads(tf.read_text(encoding="utf-8")) if tf.exists() else {}
    bed = np.zeros_like(fx)
    for key, (label, t0, t1, opts) in CUES.items():
        k = picks.get(key, "a")
        if k == "x":
            continue
        mid = next(m for kk, _, m in opts if kk == k)
        y, t, _, _ = clip(mid, key)
        y = y * 10 ** (tune.get(key, {}).get("db", 0) / 20)
        i = int((t + tune.get(key, {}).get("ms", 0) / 1000) * SR)
        bed[i:i + len(y)] += y[:len(bed) - i]
    mix = libmix.limit(np.stack([fx + bed, fx + bed], 1))
    out = HERE / "out" / "final.wav"
    sf.write(out, mix, SR, subtype="PCM_24")
    print(out, picks, f"lufs={pyln.Meter(SR).integrated_loudness(mix):.2f} peak={20*np.log10(np.abs(mix).max()):.2f}dBFS")


if __name__ == "__main__":
    export_options() if "--options" in sys.argv else render()
