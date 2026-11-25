"""Music in two parts (user's ask, round 3): part 1 under the opening struggle (K1~K3), part 2 from
"這就對了!" (K4) to the end. Part 1 stops right as the K4 caption slams down; part 2 puts a downbeat on that slam.

Candidates: game/ = the game's own music (Kevin MacLeod, CC BY 4.0: credit needed, see CREDITS.md),
mk/ = Mixkit stock music (LIB/music/<id>.mp3, free licence, no credit).
usage: python music.py --options   -> live/sfx/mus*-*.wav, appended as rows to live/sfxopts.js (run libmix.py --options first)
       python music.py             -> out/final.wav: effects mix (out/sfx-lib.wav) + music picks (music.json, music-tune.json)
"""
import json, pathlib, sys
import numpy as np, soundfile as sf, pyloudnorm as pyln, librosa
from scipy.signal import resample_poly
import libmix

HERE = pathlib.Path(__file__).parent
SR = libmix.SR
at, TOTAL = libmix.cue_times()
SPLIT = at["slam@450"]          # K4 starts: part 1 ends, part 2 begins
HIT = SPLIT + 0.27              # the caption slams down here: part 2's first downbeat
LEVEL = -24.0                   # bed loudness, under the effects (mastered at -18)
GAME = pathlib.Path(libmix.K["game"])

# part id -> (label, start, end, [(key, label, source)])
CUES = {
    "mus1": ("配樂第一段 (開場 ~ 跳坑)", 0.0, SPLIT, [
        ("a", "遊戲標題曲 Monkeys Spinning Monkeys (遊戲原曲)", "game:music_title"),
        ("b", "搞笑 Comical", "mk:2"),
        ("c", "笨手笨腳 Clumsy Daddy", "mk:827"),
        ("d", "開玩笑 Kidding Around", "mk:9"),
    ]),
    "mus2": ("配樂第二段 (這就對了 ~ 片尾)", SPLIT, TOTAL, [
        ("a", "遊戲通關曲 Life of Riley (遊戲原曲)", "game:music_ending"),
        ("b", "歡樂遊戲 Fun and Games", "mk:6"),
        ("c", "遊戲機 Game Boy", "mk:491"),
        ("d", "遊戲時間快到了 Almost Game Time", "mk:75"),
    ]),
}


def track(src):
    kind, mid = src.split(":")
    f = GAME / f"{mid}.mp3" if kind == "game" else libmix.LIB / "music" / f"{mid}.mp3"
    x, sr = sf.read(f, always_2d=True)
    x = x.mean(1)
    return resample_poly(x, SR, sr) if sr != SR else x


def downbeats(x):
    y = librosa.resample(x, orig_sr=SR, target_sr=22050)
    tempo, beats = librosa.beat.beat_track(y=y, sr=22050, units="time")
    onset = librosa.onset.onset_strength(y=y, sr=22050)
    rms = librosa.feature.rms(y=y)[0]
    return float(np.atleast_1d(tempo)[0]), beats, onset, rms


def pick_start(x, length, lead, skip):
    """a beat `lead` seconds into the excerpt, chosen for a strong hit and steady energy after it."""
    bpm, beats, onset, rms = downbeats(x)
    fr = lambda t: min(len(rms) - 1, int(t * 22050 / 512))
    best, score = beats[0], -1e9
    for b in beats:
        s = b - lead
        if s < skip or s + length > len(x) / SR - 1:
            continue
        seg = rms[fr(s):fr(s + length)]
        sc = onset[fr(b)] / (onset.mean() + 1e-9) * 0.02 + seg.mean() - 0.5 * seg.std()
        if sc > score:
            best, score = b, sc
    return best - lead, bpm


def clip(src, key):
    """the part's music at its final level, starting at the part's start time."""
    _, t0, t1, _ = CUES[key]
    x = track(src)
    length = t1 - t0
    if key == "mus1":
        s, bpm = pick_start(x, length, 0.0, 0.0)           # open on a beat, right from the first frame
        fin, fout = 0.25, 0.12                             # cut off just before the slam
    else:
        s, bpm = pick_start(x, length, HIT - t0, 2.0)      # a strong beat lands on the slam
        fin, fout = 0.05, 1.2
    i = max(0, int(s * SR))
    y = x[i:i + int(length * SR)].copy()
    y = np.pad(y, (0, int(length * SR) - len(y)))
    f = int(fin * SR); y[:f] *= np.sin(np.linspace(0, np.pi / 2, f)) ** 2
    g = int(fout * SR); y[-g:] *= np.cos(np.linspace(0, np.pi / 2, g)) ** 2
    body = y[f:len(y) - g]
    y = y * 10 ** ((LEVEL - pyln.Meter(SR).integrated_loudness(np.stack([body, body], 1))) / 20)
    return y, t0, s, bpm


def export_options():
    od = HERE.parent / "live" / "sfx"
    for f in od.glob("mus*.wav"):
        f.unlink()
    rows = []
    for key, (label, t0, t1, opts) in CUES.items():
        ro = {"id": key, "label": label, "opts": []}
        for k, name, src in opts:
            y, t, s, bpm = clip(src, key)
            fn = f"{key}-{k}.wav"
            sf.write(od / fn, libmix.limit(y[:, None], ceil=0.89)[:, 0], SR, subtype="PCM_16")
            ro["opts"].append({"key": k, "label": name, "clips": [{"t": round(t, 4), "src": f"sfx/{fn}"}]})
            print(f"{key} {k} {name}: track from {s:.2f}s, {bpm:.0f} BPM")
        ro["opts"].append({"key": "x", "label": "不要音樂", "clips": []})
        rows.append(ro)
    js = HERE.parent / "live" / "sfxopts.js"
    txt = js.read_text(encoding="utf-8")
    txt += "// the two music parts (audio/music.py --options), as two more rows\nwindow.VID_SFX = window.VID_SFX.concat(" + json.dumps(rows, ensure_ascii=False) + ");\n"
    js.write_text(txt, encoding="utf-8")


def render():
    fx, _ = sf.read(HERE / "out" / "sfx-lib.wav", always_2d=True)
    fx = fx.mean(1)
    pf, tf = HERE / "music.json", HERE / "music-tune.json"
    picks = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else {}
    tune = json.loads(tf.read_text(encoding="utf-8")) if tf.exists() else {}
    bed = np.zeros_like(fx)
    for key, (label, t0, t1, opts) in CUES.items():
        k = picks.get(key, "a")
        if k == "x":
            continue
        src = next(m for kk, _, m in opts if kk == k)
        y, t, _, _ = clip(src, key)
        y = y * 10 ** (tune.get(key, {}).get("db", 0) / 20)
        i = int((t + tune.get(key, {}).get("ms", 0) / 1000) * SR)
        bed[i:i + len(y)] += y[:len(bed) - i]
    mix = libmix.limit(np.stack([fx + bed, fx + bed], 1))
    out = HERE / "out" / "final.wav"
    sf.write(out, mix, SR, subtype="PCM_24")
    print(out, picks, f"lufs={pyln.Meter(SR).integrated_loudness(mix):.2f} peak={20*np.log10(np.abs(mix).max()):.2f}dBFS")


if __name__ == "__main__":
    export_options() if "--options" in sys.argv else render()
