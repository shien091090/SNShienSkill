// film.js — the whole video as one GSAP timeline. Contract used by index.html (review page),
// test.html (render harness), tools/renderfilm.mjs and tools/sfxcues.mjs. Every DOM query is scoped
// to `host`, so one page can hold many films (the review page builds one per option preview).
//
// Edit per project: FORMATS (only the ones this video ships), KEYFRAMES, OPTIONS, DUR, CSS, fontsFor,
// stageHTML and the per-keyframe blocks inside build(). Keep the rest as is.
(function (root) {
  // Output formats. picks.fmt selects one; the first is the main format the options are judged in.
  const FORMATS = {
    sq: { W: 1080, H: 1080 },  // IG
    por: { W: 1080, H: 1920 }, // Reels/Threads/TikTok/Shorts/website
  };
  const fmtOf = (picks) => (FORMATS[picks && picks.fmt] ? picks.fmt : Object.keys(FORMATS)[0]);
  const size = (picks) => FORMATS[fmtOf(picks)];

  // [id, start, dur] in 1x seconds. Sum of durations (after DUR) / SPEED = the video length the user asked for.
  const KEYFRAMES = [
    ["k1", 0, 2.0],
    ["k2", 2.0, 2.0],
  ].map(([id, o, d]) => ({ id, o, d }));

  // This round's options per keyframe. "0" = what is already chosen (the baseline). Empty object = no options.
  // Round 1 has no baseline yet, so its keys are "a".."d" only.
  const OPTIONS = {
    k1: ["a", "b", "c"],
    k2: ["a", "b", "c"],
  };

  // Length overrides per keyframe that depend on the picks, e.g. { k2: pick("k2") === "b" ? 2.6 : 2.0 }.
  const DUR = (pick) => ({});

  const SPEED = 1; // global playback speed; tune this before retiming single keyframes

  const CSS = `
    .vid { position:absolute; inset:0; overflow:hidden; background:#fff; color:#111;
           font-family:"Noto Sans TC",sans-serif; }
    .vid .t { position:absolute; left:0; right:0; text-align:center; font-weight:900; }
  `;

  // Font specs the host must load (document.fonts.load) before build(); text is measured at build time.
  const FONT_SAMPLE = "影片標題";
  const fontsFor = (picks) => ['900 100px "Noto Sans TC"'];

  function stageHTML(L) {
    return `<div class="t" id="title" style="top:${L.H * 0.42}px;font-size:${L.W * 0.1}px">影片標題</div>`;
  }

  function build(host, picks = {}) {
    const pick = (id) => (OPTIONS[id] && OPTIONS[id].includes(picks[id]) ? picks[id] : "0");
    const L = size(picks);
    const over = DUR(pick);
    const starts = {}, durs = {};
    let acc = 0;
    for (const k of KEYFRAMES) { starts[k.id] = acc; durs[k.id] = over[k.id] ?? k.d; acc += durs[k.id]; }
    const total = acc;
    // map an original (1x, un-retimed) absolute time onto the retimed timeline
    const at = (t) => {
      const k = KEYFRAMES.findLast((x) => t >= x.o) || KEYFRAMES[0];
      return starts[k.id] + Math.min(t - k.o, durs[k.id]);
    };

    const film = document.createElement("div");
    film.className = "vid";
    film.style.width = L.W + "px";
    film.style.height = L.H + "px";
    film.innerHTML = stageHTML(L);
    host.innerHTML = "";
    host.appendChild(film);
    const $ = (s) => film.querySelector(s);

    const tl = gsap.timeline({ paused: true });
    const sfx = [];
    // a sound cue sits at the picture event that causes it; id is stable across retimes (sfxcues adds @frame)
    const cue = (kind, t, o = {}) => sfx.push({ kind, t, id: o.id || kind, ...o });

    // initial states, set explicitly so seeking backwards and looping replay the same
    tl.set($("#title"), { opacity: 0, y: 40 }, 0);

    // ===== K1 · 片名進場 =====
    {
      const s = starts.k1, k = pick("k1");
      if (k === "b") tl.fromTo($("#title"), { opacity: 0, scale: 1.4 }, { opacity: 1, scale: 1, y: 0, duration: 0.6, ease: "back.out(2)", immediateRender: false }, s);
      else if (k === "c") tl.fromTo($("#title"), { opacity: 0, x: -200 }, { opacity: 1, x: 0, y: 0, duration: 0.5, ease: "power3.out", immediateRender: false }, s);
      else tl.to($("#title"), { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" }, s);
      cue("title", s + 0.1);
    }

    // ===== K2 · 片名退場 =====
    {
      const s = starts.k2, k = pick("k2");
      if (k === "b") tl.to($("#title"), { opacity: 0, scale: 0.6, duration: 0.4, ease: "power2.in" }, s + 1.2);
      else if (k === "c") tl.to($("#title"), { y: -L.H, duration: 0.5, ease: "power3.in" }, s + 1.2);
      else tl.to($("#title"), { opacity: 0, duration: 0.4 }, s + 1.2);
      cue("out", s + 1.2);
    }

    tl.set({}, {}, total); // pad to the full length
    tl.timeScale(SPEED).paused(false);
    const out = gsap.timeline({ paused: true });
    out.add(tl, 0);
    const fast = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v / SPEED]));
    return {
      tl: out, total: total / SPEED, starts: fast(starts), durs: fast(durs), film,
      sfx: sfx.map((c) => ({ ...c, t: c.t / SPEED })),
    };
  }

  root.VID = { FORMATS, size, KEYFRAMES, OPTIONS, SPEED, CSS, FONT_SAMPLE, fontsFor, build };
})(window);
