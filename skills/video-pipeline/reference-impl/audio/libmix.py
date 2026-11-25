"""Mix the film's effects track from CC0 library samples (Kenney + OpenGameArt).

Times come from cues.json (exported from film.js), looked up by cue id, so the
track follows the picture when the film is re-timed. Only the cues listed in
PLAN sound; everything else in cues.json stays silent on purpose.
The review page offers alternatives per sound moment (moments.py); picks.json holds the choice.
usage: python libmix.py              -> out/sfx-lib.wav from picks.json + tune.json (missing = defaults)
       python libmix.py --options    -> live/sfx/*.wav clips + live/sfxopts.js for the review page
"""
import json, os, pathlib, subprocess
import numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.signal import resample_poly

HERE = pathlib.Path(__file__).parent
# the sample library: SFX_LIB, else the folder named in libpath.txt (a library shared with an earlier video), else ./lib
_lp = HERE / "libpath.txt"
LIB = pathlib.Path(os.environ.get("SFX_LIB") or (_lp.read_text(encoding="utf-8").strip() if _lp.exists() else HERE / "lib"))
# gameplay recordings for "rec/<file>:<start s>" layers (the game's own sound under a cut); REC_DIR overrides
REC = pathlib.Path(os.environ.get("REC_DIR", r"E:\Project\Videos\_素材\遊戲實機"))
FFMPEG = json.loads((HERE.parent / "video.config.json").read_text(encoding="utf-8"))["ffmpeg"]
SR = 48000
TARGET = -18.0  # effects-only track: sparse hits, so integrated loudness sits lower
# "game" points at the featured game's own sound folder; the path below is 接力吉尼's on the original machine — change it per video
K = {"lab": "lab", "mk": "mixkit", "ui": "interface-sounds/Audio", "imp": "impact-sounds/Audio", "cas": "casino-audio/Audio",
     "rpg": "rpg-audio/Audio", "dig": "digital-audio/Audio", "oga": "oga/swishes/swishes", "air": "oga",
     "game": "E:/Project/Game/WebGame_GhostEchoV2/release/game/audio/assets"}  # 接力吉尼自己的音效 (CC0)

# cue id -> list of layers: (file, loudness LUFS of that layer on its own, offset s, options)
# options: semi = pitch shift, cut = (start, length) slice of the sample, hp = high-pass Hz, len = max length s
from moments import PLAN  # the default ("0") layers live next to the moments


def load(name, o):
    pre, rest = name.split("/", 1)
    if pre == "rec":  # a slice of a gameplay recording's own audio: "rec/bubble-tempo.mp4:52.65", o["len"] seconds
        f, t = rest.rsplit(":", 1)
        n = o.get("len", 0.4)
        raw = subprocess.run([FFMPEG, "-v", "error", "-ss", t, "-i", str(REC / f), "-t", str(n), "-vn", "-ac", "1", "-ar", str(SR),
                              "-f", "f32le", "-"], capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.float32).astype(np.float64).copy()
        f1, f2 = int(0.01 * SR), int(0.06 * SR)
        x[:f1] *= np.linspace(0, 1, f1); x[-f2:] *= np.linspace(1, 0, f2)
        return x / (np.abs(x).max() + 1e-9)
    if pre == "ov":  # Openverse files are named by id; the plan gives an id prefix
        p = next((LIB / "ov").glob(rest + "*"))
    else:
        p = (LIB / K[pre] / rest).resolve()
        if p.suffix == "":
            p = p.with_suffix({"oga": ".wav", "air": ".wav", "mk": ".mp3"}.get(pre, ".ogg"))
    x, sr = sf.read(p, always_2d=True)
    x = x.mean(1)
    if sr != SR:
        x = resample_poly(x, SR, sr)
    if "cut" not in o:
        # library files often start with silence: begin at the first audible sample
        on = np.nonzero(np.abs(x) > np.abs(x).max() * 10 ** (-36 / 20))[0]
        x = x[max(0, on[0] - int(0.002 * SR)):] if len(on) else x
        n = int(o.get("len", 2.0) * SR)
        if len(x) > n:
            x = x[:n].copy()
            f = min(int(0.3 * SR), n // 2)
            x[-f:] *= np.linspace(1, 0, f) ** 2
    if "cut" in o:
        a, n = o["cut"]
        x = x[int(a * SR):int((a + n) * SR)].copy()
        f = int(0.08 * SR)
        x[:f] *= np.linspace(0, 1, f) ** 2
        x[-f * 3:] *= np.linspace(1, 0, f * 3) ** 2
    if o.get("hp"):  # high-pass in Hz: takes the weight (thump) out of a sound
        from scipy.signal import butter, sosfilt
        x = sosfilt(butter(4, o["hp"], "highpass", fs=SR, output="sos"), x)
    if o.get("semi"):
        r = 2 ** (o["semi"] / 12)  # faster playback = higher pitch
        up, dn = 1000, int(round(1000 * r))
        x = resample_poly(x, up, dn)
    x = x / (np.abs(x).max() + 1e-9)
    return x


def loud(x):
    # loudest 100 ms, K-weighted: short sounds are judged by their attack, not their tail
    m = pyln.Meter(SR, block_size=0.1)
    y = np.pad(x, (0, max(0, int(0.4 * SR) - len(x))))
    return m.integrated_loudness(np.stack([y, y], 1)) + 3.0


def limit(x, ceil=0.71, rel=0.08):  # -3 dBFS sample peak leaves room for AAC/MP3 overshoot
    # peak limiter: instant attack (5 ms look-ahead), exponential release
    la = int(0.005 * SR)
    pk = np.abs(x).max(1)
    need = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    need = np.concatenate([need[la:], np.ones(la)])
    from scipy.ndimage import minimum_filter1d
    need = minimum_filter1d(need, la * 2 + 1)
    g = np.empty_like(need); a = np.exp(-1 / (rel * SR)); c = 1.0
    for i, v in enumerate(need):
        c = v if v < c else v + (c - v) * a
        g[i] = c
    return x * g[:, None]


from moments import MOMENTS


def option(m, key):
    """cue id -> layers for one moment's option."""
    mid, name, cues, opts = m
    if key == "x":
        return {}
    if key == "0" or key not in opts:
        return {c: PLAN[c] for c in cues if c in PLAN}
    return opts[key][1]


def plan_for(picks, tune=None):
    """tune: moment id -> {"db": gain, "ms": shift} from the review page's fine-tuning (tune.json)."""
    plan = {}
    for m in MOMENTS:
        t = (tune or {}).get(m[0], {})
        g, dt = t.get("db", 0), t.get("ms", 0) / 1000
        for cid, layers in option(m, picks.get(m[0], "0")).items():
            plan[cid] = [(nm, db + g, off + dt, o) for nm, db, off, o in layers]
    return plan


def cue_times():
    # cue ids carry their frame ("votes@507"), and this file and moments.py name cues by the ids of cues.base.json
    # (the timing they were picked on). A retimed film keeps those names: the n-th cue of a kind in cues.json
    # answers to the n-th id of that kind in cues.base.json; kinds the base never had keep their own ids.
    cues = json.loads((HERE / "cues.json").read_text(encoding="utf-8"))
    base = json.loads((HERE / "cues.base.json").read_text(encoding="utf-8"))
    kind = lambda cid: cid.rsplit("@", 1)[0]
    names = {}
    for e in base["events"]:
        names.setdefault(kind(e["id"]), []).append(e["id"])
    at, seen = {}, {}
    for e in cues["events"]:
        k = kind(e["id"]); n = seen.get(k, 0); seen[k] = n + 1
        old = names.get(k, [])
        at[old[n] if n < len(old) else e["id"]] = e["f"] / cues["fps"]
    return at, cues["total"]  # sfxcues.mjs writes total in seconds


def check():
    at, _ = cue_times()
    owned = {c for m in MOMENTS for c in m[2]}
    used = set(PLAN) | {c for m in MOMENTS for k, v in m[3].items() if k != "0" for c in v[1]}
    bad = sorted(c for c in used if c not in at)
    loose = sorted(c for c in PLAN if c not in owned)
    if bad or loose:
        raise SystemExit(f"cue ids not in cues.json: {bad}; PLAN cues outside every moment: {loose}")
    return at


def layer(name, lufs, off, o):
    """(samples at their loudness role, start offset from the cue); align="peak" lands the loudest point on the cue."""
    x = load(name, o)
    if o.get("align") == "peak":
        off -= int(np.argmax(np.abs(x))) / SR
    return x * 10 ** ((lufs - loud(x)) / 20), off


def raw_mix(plan, at, total):
    mix = np.zeros(int((total + 1.0) * SR))
    for cid, layers in plan.items():
        for name, db, off, o in layers:
            x, off = layer(name, db, off, o)
            i = max(0, int((at[cid] + off) * SR))
            n = min(len(x), len(mix) - i)
            mix[i:i + n] += x[:n]
    return mix


def master(mono):
    mix = np.stack([mono, mono], 1)
    meter = pyln.Meter(SR)
    for _ in range(3):  # limiting lowers loudness a little; converge on the target
        mix = limit(pyln.normalize.loudness(mix, meter.integrated_loudness(mix), TARGET))
    fade = int(0.8 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return mix, meter.integrated_loudness(mix)


def render():
    at = check()
    _, total = cue_times()
    pf = HERE / "picks.json"
    picks = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else {}
    tf = HERE / "tune.json"
    tune = json.loads(tf.read_text(encoding="utf-8")) if tf.exists() else {}
    plan = plan_for(picks, tune)
    # the same gain the review page's clips were made with (the default mix brought to TARGET), so the picked
    # sounds keep the levels the user heard them at against the music; no re-normalising of the picked mix
    meter = pyln.Meter(SR)
    d = raw_mix(plan_for({}), at, total)
    gain = 10 ** ((TARGET - meter.integrated_loudness(np.stack([d, d], 1))) / 20)
    m = raw_mix(plan, at, total) * gain
    mix = limit(np.stack([m, m], 1))
    fade = int(0.8 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    lufs = meter.integrated_loudness(mix)
    out = HERE / "out" / "sfx-lib.wav"
    out.parent.mkdir(exist_ok=True)
    sf.write(out, mix, SR, subtype="PCM_24")
    print(f"{out}  picks={picks} tune={tune} events={sum(len(v) for v in plan.values())} "
          f"lufs={lufs:.2f} peak={20*np.log10(np.abs(mix).max()):.2f}dBFS")


def export_options():
    """One mono wav per (moment, option, cue) for the review page, pre-scaled by the default mix's master gain."""
    at = check()
    _, total = cue_times()
    meter = pyln.Meter(SR)
    d = raw_mix(plan_for({}), at, total)
    gain = 10 ** ((TARGET - meter.integrated_loudness(np.stack([d, d], 1))) / 20)
    od = HERE.parent / "live" / "sfx"
    od.mkdir(exist_ok=True)
    for f in od.glob("*.wav"):
        f.unlink()
    rows = []
    for m in MOMENTS:
        mid, name, cues, opts = m
        keys = ["0"] + [k for k in opts if k != "0"] + ["x"]
        ro = {"id": mid, "label": name, "opts": []}
        for key in keys:
            plan = option(m, key)
            label = "不要音效" if key == "x" else (opts["0"] if key == "0" else opts[key][0])
            clips = []
            for cid, layers in plan.items():
                ys = [layer(nm, db, off, o) for nm, db, off, o in layers]
                first = min(off for _, off in ys)
                x = np.zeros(int(6 * SR))
                for y, off in ys:
                    y = y * gain
                    i = int((off - first) * SR)
                    x[i:i + len(y)] += y[:len(x) - i]
                nz = np.nonzero(np.abs(x) > 10 ** (-66 / 20))[0]
                x = limit(x[:nz[-1] + 1 if len(nz) else 1][:, None], ceil=0.89)[:, 0]  # like the final mix's limiter
                fn = f"{mid}-{key}-{len(clips)}.wav"
                sf.write(od / fn, x, SR, subtype="PCM_16")
                clips.append({"t": round(at[cid] + first, 4), "src": f"sfx/{fn}"})
            ro["opts"].append({"key": key, "label": label, "clips": clips})
        rows.append(ro)
    js = "// sound moments and their options, written by audio/libmix.py --options\nwindow.VID_SFX = " + json.dumps(rows, ensure_ascii=False) + ";\n"
    (HERE.parent / "live" / "sfxopts.js").write_text(js, encoding="utf-8")
    n = sum(len(o["clips"]) for r in rows for o in r["opts"])
    size = sum(f.stat().st_size for f in od.glob("*.wav"))
    print(f"{len(rows)} moments, {n} clips, {size/1e6:.1f} MB")


if __name__ == "__main__":
    import sys
    export_options() if "--options" in sys.argv else render()
