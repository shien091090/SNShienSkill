"""Mix the film's effects track from CC0 library samples (Kenney + OpenGameArt).

Times come from cues.json (exported from film.js), looked up by cue id, so the
track follows the picture when the film is re-timed. Only the cues listed in
PLAN sound; everything else in cues.json stays silent on purpose.
The review page offers alternatives per sound moment (moments.py); picks.json holds the choice.
usage: python libmix.py              -> out/sfx-lib.wav from picks.json + tune.json (missing = defaults)
       python libmix.py --options    -> live/sfx/*.wav clips + live/sfxopts.js for the review page
"""
import json, pathlib
import numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.signal import resample_poly

HERE = pathlib.Path(__file__).parent
LIB = HERE / "lib"
SR = 48000
TARGET = -18.0  # effects-only track: sparse hits, so integrated loudness sits lower
K = {"lab": "lab", "mk": "mixkit", "ui": "interface-sounds/Audio", "imp": "impact-sounds/Audio", "cas": "casino-audio/Audio",
     "rpg": "rpg-audio/Audio", "dig": "digital-audio/Audio", "oga": "oga/swishes/swishes", "air": "oga"}

# cue id -> list of layers: (file, loudness LUFS of that layer on its own, offset s, options)
# options: semi = pitch shift, cut = (start, length) slice of the sample, hp = high-pass Hz, len = max length s
PLAN = {
    "title:0@17":          [("ui/maximize_007", -21, 0, {})],
    "spread@98":           [("air/air-whoosh.wav", -22, -0.15, {"cut": (1.6, 1.0)})],
    "focus:ring@161":      [("cas/card-slide-3", -27, 0, {})],
    "focus-hit:ring@169":  [("imp/impactPlate_light_000", -18, 0, {})],
    "tile:3@217":          [("cas/card-fan-1", -20, 0, {})],
    "play:wan@274":        [("ui/toggle_002", -25, 0, {})],
    "focus:check@386":     [("cas/card-slide-5", -27, 0, {})],
    "focus-hit:check@395": [("ui/confirmation_003", -18, 0, {})],
    "wall-down@468":       [("imp/impactWood_medium_002", -18, 0, {})],
    "vote:text@497":       [("ui/select_004", -21, 0, {})],
    "votes@507":           [("cas/chips-handle-2", -21, 0, {})],
    "fun:jump@531":        [("ui/confirmation_002", -17, 0, {})],
    "chips-fly@634":       [("cas/card-slide-2", -27, 0, {})],
    "chip-in:0@641":       [("cas/chips-collide-3", -23, 0, {})],
    "chip-in:5@665":       [("cas/chips-stack-5", -25, 0, {})],
    "r2-in@701":           [("cas/card-slide-7", -28, 0, {})],
    "votes@719":           [("cas/chips-handle-1", -22, 0, {})],
    "chip-in:0@835":       [("cas/chips-collide-1", -23, 0, {})],
    "chip-in:5@859":       [("cas/chips-stack-2", -25, 0, {})],
    "hero-zoom@902":       [("air/air-whoosh.wav", -24, -0.1, {"cut": (2.0, 0.7)})],
    "stamp@938":           [("imp/impactPunch_heavy_002", -13, 0, {}), ("rpg/bookPlace2", -18, 0, {})],
    "focus:gear@1025":     [("cas/card-slide-4", -27, 0, {})],
    "focus-hit:gear@1033": [("rpg/metalLatch", -19, 0, {})],
    "gear:1@1047":         [("rpg/metalClick", -24, 0, {})],
    "screen-in@1104":      [("cas/card-slide-1", -27, 0, {})],
    "crack@1123":          [("imp/impactGlass_heavy_001", -19, 0, {})],
    "shards@1178":         [("imp/impactGlass_light_002", -22, 0, {})],
    "transform@1247":      [("ui/glass_004", -21, 0, {})],
    "hero-jump@1269":      [("dig/phaseJump5", -25, 0, {})],
    "coin:0@1284":         [("dig/powerUp6", -21, 0, {"semi": 0})],
    "coin:1@1295":         [("dig/powerUp6", -20, 0, {"semi": 2})],
    "coin:2@1321":         [("dig/powerUp6", -19, 0, {"semi": 4})],
    "enemy-land@1355":     [("imp/impactSoft_heavy_001", -16, 0, {})],
    "sword-draw@1359":     [("rpg/drawKnife3", -21, 0, {})],
    "leap@1380":           [("oga/swish-9", -21, -0.05, {})],
    "slash-hit@1388":      [("rpg/knifeSlice2", -13, -0.03, {}), ("imp/impactPunch_medium_002", -14, 0, {})],
    "enemy-puff@1399":     [("rpg/cloth1", -25, 0, {})],
    "3d-swing@1464":       [("air/air-whoosh.wav", -20, -0.2, {"cut": (1.2, 2.6)})],
    "steam-win@1607":      [("ui/maximize_002", -21, 0, {})],
    "steam-seat@1649":     [("ui/switch_003", -20, 0, {})],
    "box-up@1766":         [("cas/card-slide-8", -25, 0, {})],
    "lid@1822":            [("rpg/bookClose", -16, 0, {})],
    "sparkle:0@1863":      [("ui/glass_004", -21, 0, {})],
    "lockup@1954":         [("imp/impactBell_heavy_000", -18, 0, {})],
}


def load(name, o):
    pre, rest = name.split("/", 1)
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
    return at, cues["total"] / cues["fps"]


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
    mix, lufs = master(raw_mix(plan, at, total))
    out = HERE / "out" / "sfx-lib.wav"
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
