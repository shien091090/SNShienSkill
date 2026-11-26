// film.js — the whole video as one GSAP timeline. Contract used by index.html (review page),
// test.html (render harness), tools/renderfilm.mjs and tools/sfxcues.mjs. Every DOM query is scoped
// to `host`, so one page can hold many films (the review page builds one per option preview).
//
// 接力吉尼 30 秒介紹 (PVD 網站 trailer, 1280×720)。實機畫面走「片段」: 審閱頁用 clips/*.mp4 (全關鍵格, 逐格 seek),
// 渲染 (test.html 設 VID_RENDER) 用 capture/ 底下的 1280×720 原始畫格; 每次 seek 後 FILM.settle() 等畫格畫好。
(function (root) {
  const FORMATS = {
    wide: { W: 1280, H: 720 }, // PVD 網站試玩頁「30 秒介紹」彈窗
  };
  const fmtOf = (picks) => (FORMATS[picks && picks.fmt] ? picks.fmt : Object.keys(FORMATS)[0]);
  const size = (picks) => FORMATS[fmtOf(picks)];

  const KEYFRAMES = [
    ["k1", 0, 2.0],
    ["k2", 2.0, 2.5],
    ["k3", 4.5, 3.0],
    ["k4", 7.5, 3.2],
    ["k5", 10.7, 3.5],
    ["k6", 14.2, 5.0],
    ["k7", 19.2, 3.5],
    ["k8", 22.7, 4.0],
  ].map(([id, o, d]) => ({ id, o, d }));

  const OPTIONS = {
    k1: [], k2: [], k3: [], k4: [], k5: [], k6: [], k7: [], k8: [],
  };
  const DUR = (pick) => ({});
  const SPEED = 1;

  // 實機片段: 渲染用原始畫格 (dir/f####.jpg, 從 first 起), 審閱頁用 clips/<id>.mp4 (第 i 格在 (i+0.5)/30 秒)
  const CLIPS = {
    l1a: { dir: "capture/l1", first: 0, n: 400 },
    l1b: { dir: "capture/l1", first: 900, n: 528 },
    gate: { dir: "capture/rec/gate", first: 280, n: 141 },
    lift: { dir: "capture/rec/lift", first: 180, n: 121 },
    hook: { dir: "capture/rec/hook", first: 40, n: 91 },
    aim: { dir: "capture/rec/aim", first: 55, n: 81 },
    seesaw: { dir: "capture/rec/seesaw", first: 1, n: 150 },
    ending: { dir: "capture/rec/ending", first: 60, n: 241 },
  };

  const NAVY = "#0d1226", YEL = "#ffd84a", RED = "#ff4d5e";
  const CSS = `
    .vid { position:absolute; inset:0; overflow:hidden; background:#1a2138; color:#fff; font-family:"Noto Sans TC",sans-serif; }
    .vid .abs { position:absolute; }
    .vid #shake { position:absolute; inset:0; }
    .vid .cam { position:absolute; left:0; top:0; width:1280px; height:720px; transform-origin:0 0; }
    .vid canvas { display:block; width:100%; height:100%; }
    .vid .fx { position:absolute; inset:0; pointer-events:none; }
    .vid .cap { position:absolute; left:0; right:0; bottom:58px; text-align:center; font-weight:900; font-size:52px; line-height:1.15;
      color:#fff; -webkit-text-stroke:12px ${NAVY}; paint-order:stroke fill; text-shadow:0 6px 0 rgba(0,0,0,.35); white-space:nowrap; }
    .vid .cap .x { color:${YEL}; display:inline-block; }
    .vid .cap .ch { display:inline-block; }
    .vid .ov { position:absolute; inset:0; pointer-events:none; }
    .vid .bar { position:absolute; left:0; right:0; height:90px; background:#05070c; }
    .vid .pill { display:inline-block; padding:10px 30px; border-radius:999px; font-weight:900; font-size:46px; color:${NAVY};
      background:${YEL}; box-shadow:0 8px 0 rgba(0,0,0,.35); }
    .vid .cell, .vid .card { position:absolute; overflow:hidden; border-radius:14px; border:4px solid #fff; box-shadow:0 14px 30px rgba(0,0,0,.45); background:#1a2138; }
    .vid .stamp { position:absolute; font-weight:900; color:${NAVY}; background:${YEL}; padding:8px 22px; border-radius:10px; font-size:40px;
      border:4px solid ${NAVY}; box-shadow:0 6px 0 rgba(0,0,0,.35); white-space:nowrap; }
    .vid .k8t .pill { font-size:84px; padding:14px 46px; border:6px solid ${NAVY}; box-shadow:0 12px 0 rgba(0,0,0,.4); white-space:nowrap; }
  `;

  const CAPS = {
    c1: "平台跳躍+解謎", c1x: "....? 根本跳不上去!", c3: "不知道怎麼辦只好去死一死", c4a: "這就對了!", c4b: "靠死亡才能推進關卡",
    c5: "總共3條命", c6: "和死前的自己合作解開謎題", c7: "或許也可以做成和死前的自己一起戰鬥?",
  };
  const FONT_SAMPLE = Object.values(CAPS).join("") + "未來計畫靠死亡推進平台跳躍!?POWHITCOMBO×+＋0123456789";
  const fontsFor = (picks) => ['900 52px "Noto Sans TC"', '700 40px "Noto Sans TC"'];

  // 漫畫的生氣符號 (四段弧線)
  const ANGER = `<svg viewBox="-50 -50 100 100" width="100%" height="100%"><g fill="none" stroke="${RED}" stroke-width="13" stroke-linecap="round">
    <path d="M-10,-40 Q-12,-12 -40,-10"/><path d="M10,-40 Q12,-12 40,-10"/><path d="M-10,40 Q-12,12 -40,10"/><path d="M10,40 Q12,12 40,10"/></g></svg>`;
  const BURST = `<svg viewBox="-50 -50 100 100" width="100%" height="100%"><polygon fill="${YEL}" stroke="${NAVY}" stroke-width="4"
    points="0,-48 10,-16 44,-24 18,0 44,24 10,16 0,48 -10,16 -44,24 -18,0 -44,-24 -10,-16"/></svg>`;

  // ===== K7 示意圖 (非遊戲畫面) =====
  // 吉尼角色: 中心 (0,0), 腳底 y=28; ghost = 半透明虛線 (前一代)
  const J = (num, ghost, fill) => `<rect x="-22" y="-30" width="44" height="58" rx="12" fill="${fill || (ghost ? "rgba(150,175,235,.35)" : "#fff3c4")}"
      stroke="${ghost ? "#b8c6ff" : NAVY}" stroke-width="4" ${ghost ? 'stroke-dasharray="7 5"' : ""}/>
    <rect x="-11" y="-16" width="7" height="10" rx="2" fill="${NAVY}"/><rect x="4" y="-16" width="7" height="10" rx="2" fill="${NAVY}"/>
    <text x="0" y="20" text-anchor="middle" font-size="18" font-weight="900" fill="${NAVY}">${num}</text>`;
  // 史萊姆: 中心 (0,0), 底 y=40
  const SL = (col = "#e2566a") => `<path d="M-80,40 Q-90,-50 0,-60 Q90,-50 80,40 Z" fill="${col}" stroke="${NAVY}" stroke-width="6"/>
    <path d="M-40,-18 L-14,-6 M40,-18 L14,-6" stroke="${NAVY}" stroke-width="7" stroke-linecap="round"/>
    <circle cx="-26" cy="4" r="8" fill="${NAVY}"/><circle cx="26" cy="4" r="8" fill="${NAVY}"/>`;
  // 外層 g 給 GSAP 動 (x/y/scale/rotation), 內層 g 放定位
  const at = (id, x, y, sc, inner) => `<g id="${id}"><g transform="translate(${x},${y}) scale(${sc})">${inner}</g></g>`;
  const STAR = (r, fill = YEL) => { const pts = []; for (let i = 0; i < 16; i++) { const a = (i / 16) * Math.PI * 2, rr = i % 2 ? r * 0.5 : r; pts.push(`${(Math.cos(a) * rr).toFixed(1)},${(Math.sin(a) * rr).toFixed(1)}`); } return `<polygon points="${pts.join(" ")}" fill="${fill}" stroke="${NAVY}" stroke-width="5"/>`; };
  const word = (t, size, fill = YEL, sw = 10) => `<text x="0" y="0" text-anchor="middle" dominant-baseline="middle" font-size="${size}" font-weight="900" fill="${fill}" stroke="${NAVY}" stroke-width="${sw}" paint-order="stroke fill">${t}</text>`;

  // a: 漫畫三格 — 遇敵 → 踩前一代起跳 → 踩扁
  function k7Comic() {
    const panel = (i, x, rot, inner) => `<g id="k7p${i}"><g transform="translate(${x},70) rotate(${rot} 180 230)">
      <rect x="0" y="0" width="360" height="460" rx="6" fill="#fff" stroke="${NAVY}" stroke-width="8"/>
      <svg x="4" y="4" width="352" height="452" viewBox="4 4 352 452" overflow="hidden"><line x1="0" x2="360" y1="400" y2="400" stroke="${NAVY}" stroke-width="5"/>${inner}</svg></g></g>`;
    return `<svg viewBox="0 0 1280 720" width="1280" height="720" class="abs" style="left:0;top:0">
      <rect width="1280" height="720" fill="#f4ecd8"/>
      ${Array.from({ length: 40 }, (_, i) => `<line x1="${i * 64 - 400}" y1="0" x2="${i * 64 - 100}" y2="720" stroke="#eadfc4" stroke-width="14"/>`).join("")}
      ${panel(1, 50, -2, `${at("k7c1s", 265, 360, 0.95, SL())}${at("k7c1g", 150, 372, 1.5, J(2, true))}${at("k7c1j", 75, 372, 1.5, J(3))}
        ${at("k7c1q", 112, 250, 1, word("!?", 64, RED, 9))}`)}
      ${panel(2, 460, 1.5, `${at("k7c2s", 285, 360, 0.8, SL())}${at("k7c2g", 150, 372, 1.5, J(2, true))}
        <path id="k7c2a" d="M60,330 Q90,170 150,250" fill="none" stroke="${NAVY}" stroke-width="5" stroke-dasharray="1" stroke-dashoffset="1" pathLength="1" stroke-linecap="round"/>
        ${at("k7c2j", 60, 372, 1.5, J(3))}`)}
      ${panel(3, 870, -1, `${at("k7c3g", 70, 372, 1.5, J(2, true))}${at("k7c3b", 215, 330, 1, STAR(95))}${at("k7c3s", 215, 360, 1, SL())}
        ${at("k7c3j", 215, 205, 1.5, J(3))}${at("k7c3k", 215, 110, 1, word("POW!", 76, YEL, 10))}`)}
    </svg>`;
  }
  // b: 連攜攻擊 — 前一代沿著回放軌跡先撞一下, 本尊照同一條路再補一腳
  function k7Combo() {
    return `<svg viewBox="0 0 1280 720" width="1280" height="720" class="abs" style="left:0;top:0">
      <defs><linearGradient id="k7bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1b1640"/><stop offset="1" stop-color="#3b2a6b"/></linearGradient></defs>
      <rect width="1280" height="720" fill="url(#k7bg)"/>
      <rect x="0" y="470" width="1280" height="250" fill="#130f2c"/><line x1="0" x2="1280" y1="470" y2="470" stroke="#8f7bff" stroke-width="5"/>
      <path id="k7trail" d="M200,425 L470,425 Q560,300 650,425 L830,425" fill="none" stroke="#9fd0ff" stroke-width="6" stroke-dasharray="1" stroke-dashoffset="1" pathLength="1" stroke-linecap="round" opacity=".8"/>
      <g id="k7hpw"><rect x="850" y="250" width="220" height="26" rx="13" fill="#0b0920" stroke="#fff" stroke-width="4"/>
        <rect id="k7hp" x="854" y="254" width="212" height="18" rx="9" fill="#ff5b6e"/></g>
      ${at("k7bs", 960, 410, 1.5, SL())}
      <circle id="k7bf" cx="960" cy="400" r="120" fill="#fff"/>
      ${at("k7bg2", 200, 425, 1.6, J(2, true))}
      ${at("k7bj", 200, 425, 1.6, J(3))}
      ${at("k7bh1", 860, 330, 1, word("HIT!", 60, "#9fd0ff", 9))}
      ${at("k7bb", 960, 330, 1, STAR(110))}
      ${at("k7bk", 640, 150, 1, word("COMBO ×2", 104, YEL, 14))}
    </svg>`;
  }
  // c: Boss 剪影海報 — 夕陽下巨大 Boss 升起, 三代吉尼一起跳出來
  function k7Poster() {
    const rays = Array.from({ length: 18 }, (_, i) => { const a = (i / 18) * Math.PI * 2, b = a + 0.08; return `<polygon points="640,420 ${640 + Math.cos(a) * 1200},${420 + Math.sin(a) * 1200} ${640 + Math.cos(b) * 1200},${420 + Math.sin(b) * 1200}" fill="#fff" opacity=".13"/>`; }).join("");
    const hero = (num, ghost) => `<rect x="-22" y="-30" width="44" height="58" rx="12" fill="${ghost ? "rgba(20,10,40,.55)" : "#160a26"}" stroke="${ghost ? "#bfe6ff" : YEL}" stroke-width="4" ${ghost ? 'stroke-dasharray="7 5"' : ""}/>
      <rect x="-11" y="-16" width="7" height="10" rx="2" fill="${ghost ? "#bfe6ff" : YEL}"/><rect x="4" y="-16" width="7" height="10" rx="2" fill="${ghost ? "#bfe6ff" : YEL}"/>`;
    return `<svg viewBox="0 0 1280 720" width="1280" height="720" class="abs" style="left:0;top:0">
      <defs><linearGradient id="k7sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a0f45"/><stop offset=".55" stop-color="#e2405a"/><stop offset="1" stop-color="#ffb347"/></linearGradient></defs>
      <rect width="1280" height="720" fill="url(#k7sky)"/>
      <g id="k7rays">${rays}</g>
      <circle cx="640" cy="420" r="210" fill="#ffd56b"/>
      ${at("k7boss", 900, 470, 3.4, `<path d="M-80,40 Q-90,-50 0,-60 Q90,-50 80,40 Z" fill="#12091f"/><path d="M-44,-20 L-14,-6 M44,-20 L14,-6" stroke="#ff3b3b" stroke-width="6" stroke-linecap="round"/><circle cx="-26" cy="4" r="7" fill="#ff3b3b"/><circle cx="26" cy="4" r="7" fill="#ff3b3b"/>`)}
      <path d="M0,560 Q320,520 640,560 T1280,550 L1280,720 L0,720 Z" fill="#12091f"/>
      ${at("k7h1", 230, 470, 2.2, hero(1, true))}${at("k7h2", 360, 430, 2.2, hero(2, true))}${at("k7h3", 500, 385, 2.4, hero(3, false))}
    </svg>`;
  }
  // d: 分身擋子彈 — 前一代舉盾擋砲台, 本尊從後面跳過去踩爛砲台
  function k7Shield() {
    return `<svg viewBox="0 0 1280 720" width="1280" height="720" class="abs" style="left:0;top:0">
      <rect width="1280" height="720" fill="#dff1ec"/>
      ${Array.from({ length: 33 }, (_, i) => `<line x1="${i * 40}" x2="${i * 40}" y1="0" y2="720" stroke="#c8e3dc" stroke-width="2"/>`).join("")}
      ${Array.from({ length: 19 }, (_, i) => `<line y1="${i * 40}" y2="${i * 40}" x1="0" x2="1280" stroke="#c8e3dc" stroke-width="2"/>`).join("")}
      <rect x="0" y="470" width="1280" height="250" fill="#9fc9bd"/><line x1="0" x2="1280" y1="470" y2="470" stroke="${NAVY}" stroke-width="6"/>
      ${at("k7tur", 1070, 410, 1, `<rect x="-70" y="-40" width="140" height="100" rx="18" fill="#6b7896" stroke="${NAVY}" stroke-width="6"/>
        <rect x="-150" y="-22" width="90" height="34" rx="8" fill="#4a5470" stroke="${NAVY}" stroke-width="6"/>
        <circle cx="-10" cy="5" r="16" fill="${RED}" stroke="${NAVY}" stroke-width="5"/>`)}
      ${[0, 1, 2].map((i) => `<circle id="k7bul${i}" cx="900" cy="405" r="16" fill="${RED}" stroke="${NAVY}" stroke-width="5"/>`).join("")}
      ${at("k7sg", 520, 425, 1.6, J(2, true))}
      <path id="k7shd" d="M575,330 Q640,425 575,520" fill="none" stroke="#3fb8ff" stroke-width="14" stroke-linecap="round" opacity=".85"/>
      ${[0, 1, 2].map((i) => at("k7sp" + i, 600, 405, 0.45, STAR(60, "#fff"))).join("")}
      ${at("k7sj", 300, 425, 1.6, J(3))}
      ${at("k7sb", 1070, 400, 1, STAR(130))}
    </svg>`;
  }

  function stageHTML(L) {
    const cap = (id, inner) => `<div class="cap" id="${id}">${inner}</div>`;
    const chars = (s) => [...s].map((c) => `<span class="ch">${c === " " ? "&nbsp;" : c}</span>`).join("");
    return `<div id="shake">
      <div class="abs" id="camWrap" style="left:0;top:0;width:1280px;height:720px;transform-origin:50% 50%"><div class="cam" id="camA"><canvas id="cvA" width="1280" height="720"></canvas>
        <div class="fx">
          <div class="abs" id="anger" style="left:268px;top:492px;width:24px;height:24px">${ANGER}</div>
          <div class="abs" id="anger2" style="left:222px;top:520px;width:18px;height:18px">${ANGER}</div>
          <div class="abs" id="anger3" style="left:285px;top:548px;width:16px;height:16px">${ANGER}</div>
          <div class="abs" id="burst1" style="left:145px;top:600px;width:80px;height:80px">${BURST}</div>
          <div class="abs" id="burst2" style="left:430px;top:443px;width:80px;height:80px">${BURST}</div>
          <div class="abs" id="ring1" style="left:150px;top:560px;width:70px;height:110px;border:5px solid ${YEL};border-radius:18px"></div>
          <div class="abs" id="ring2" style="left:435px;top:405px;width:70px;height:110px;border:5px solid ${YEL};border-radius:18px"></div>
          <div class="abs" id="hudbox" style="left:4px;top:4px;width:240px;height:42px;border:3px solid ${YEL};border-radius:8px;box-shadow:0 0 0 3px rgba(0,0,0,.5)"></div>
        </div>
      </div></div>
      <div class="ov" id="tint" style="background:#c0283f;mix-blend-mode:multiply"></div>
      <div class="ov" id="vign" style="background:radial-gradient(ellipse at 50% 55%, rgba(0,0,0,0) 30%, rgba(0,0,0,.85) 75%)"></div>
      <div class="ov" id="speed" style="background:repeating-linear-gradient(90deg, rgba(255,255,255,0) 0 60px, rgba(255,255,255,.10) 60px 64px);
        -webkit-mask:linear-gradient(90deg,#000 0,transparent 28%,transparent 72%,#000 100%);mask:linear-gradient(90deg,#000 0,transparent 28%,transparent 72%,#000 100%)"></div>
      <div class="ov" id="rgbC" style="background:#00e5ff;mix-blend-mode:screen"></div>
      <div class="ov" id="rgbM" style="background:#ff2bd6;mix-blend-mode:screen"></div>
      <div class="abs" id="pip" style="left:840px;top:80px;width:360px;height:360px;border-radius:50%;overflow:hidden;border:6px solid #fff;box-shadow:0 12px 30px rgba(0,0,0,.5)">
        <div class="cam" id="camP"><canvas id="cvP" width="1280" height="720"></canvas>
          <div class="fx"><div class="abs" id="angerP" style="left:270px;top:470px;width:44px;height:44px">${ANGER}</div></div></div>
      </div>
      <div class="abs" id="loupe" style="left:430px;top:110px;width:420px;height:420px;border-radius:50%;overflow:hidden;border:8px solid ${YEL};box-shadow:0 14px 34px rgba(0,0,0,.55)">
        <div class="cam" id="camL"><canvas id="cvL" width="1280" height="720"></canvas></div>
      </div>
      <div class="ov" id="loupeLine"><svg width="1280" height="720"><line x1="250" y1="40" x2="480" y2="190" stroke="${YEL}" stroke-width="6" stroke-linecap="round"/></svg></div>
      <div class="ov" id="grid">${[0, 1, 2, 3].map((i) => `<div class="cell" id="g${i + 1}" style="left:${i % 2 ? 656 : 64}px;top:${i < 2 ? 40 : 330}px;width:560px;height:315px"><canvas id="cvG${i + 1}" width="1280" height="720"></canvas></div>`).join("")}</div>
      <div class="ov" id="cards">${[0, 1, 2, 3].map((i) => `<div class="card" id="cd${i + 1}" style="left:250px;top:70px;width:780px;height:439px"><canvas id="cvC${i + 1}" width="1280" height="720"></canvas></div>`).join("")}</div>
      <div class="ov" id="k7A">${k7Comic()}<div class="stamp" id="k7nA" style="left:560px;top:22px;transform:rotate(7deg);background:#ffe97a">未來計畫</div></div>
      <div class="ov" id="k7B">${k7Combo()}<div class="stamp" id="k7nB" style="left:50px;top:44px">未來計畫</div></div>
      <div class="ov" id="k7C">${k7Poster()}<div class="stamp" id="k7nC" style="left:520px;top:60px;font-size:56px;padding:10px 32px;transform:rotate(-4deg)">未來計畫</div></div>
      <div class="ov" id="k7D">${k7Shield()}<div class="stamp" id="k7nD" style="left:60px;top:50px;transform:rotate(-6deg);background:#fff;border-style:dashed">未來計畫</div></div>
      <div class="ov" id="flash" style="background:#fff"></div>
      <div class="ov" id="wipe" style="background:${YEL}"></div>
      <div class="bar" id="barT" style="top:0"></div><div class="bar" id="barB" style="bottom:0"></div>
      <div class="abs k8t" id="k8A" style="left:120px;top:290px"><span class="pill">靠死亡推進</span></div>
      <div class="abs" id="k8P" style="left:632px;top:296px;font-size:96px;line-height:1;font-weight:900;-webkit-text-stroke:14px ${NAVY};paint-order:stroke fill">＋</div>
      <div class="abs k8t" id="k8B" style="left:762px;top:290px"><span class="pill">平台跳躍</span></div>
      ${cap("c1", `<span id="c1m">${chars(CAPS.c1)}</span><span class="x" id="c1x" style="display:none">${chars(CAPS.c1x)}</span>`)}
      ${`<div class="cap" id="c3" style="bottom:auto;top:120px">${chars(CAPS.c3)}</div>`}
      <div class="cap" id="c4" style="bottom:auto;top:250px"><div id="c4a" style="font-size:120px;color:${YEL}">${CAPS.c4a}</div><div id="c4b" style="font-size:64px">${CAPS.c4b}</div></div>
      ${cap("c5", CAPS.c5)}
      ${cap("c6", chars(CAPS.c6))}
      ${cap("c7", chars(CAPS.c7))}
    </div>`;
  }

  const isRender = () => !!root.VID_RENDER;
  // 審閱頁: 開頁就把所有片段整支下載成 blob (所有播放器共用), 下載完 index.html 才建影片、從頭播。
  // 邊播邊下載的話第一次播全黑, 快閃段跳格跟不上會停在舊畫面 (馬戲團介紹影片踩過)
  const BLOB = {};
  let clipsLoaded = 0;
  const clipsReady = isRender() ? Promise.resolve() : Promise.all(Object.keys(CLIPS).map((id) => (BLOB[id] = fetch(`clips/${id}.mp4`)
    .then((r) => r.blob()).then((b) => URL.createObjectURL(b)).catch(() => `clips/${id}.mp4`)
    .then((u) => { clipsLoaded++; return (BLOB[id] = u); }))));
  root.VID_CLIPS = { ready: clipsReady, progress: () => [clipsLoaded, Object.keys(CLIPS).length] };
  const pad4 = (n) => String(n).padStart(4, "0");

  function build(host, picks = {}) {
    const pick = (id) => (OPTIONS[id] && OPTIONS[id].includes(picks[id]) ? picks[id] : "0");
    const L = size(picks);
    const over = DUR(pick);
    const starts = {}, durs = {};
    let acc = 0;
    for (const k of KEYFRAMES) { starts[k.id] = acc; durs[k.id] = over[k.id] ?? k.d; acc += durs[k.id]; }
    const total = acc;

    const film = document.createElement("div");
    film.className = "vid";
    film.style.width = L.W + "px";
    film.style.height = L.H + "px";
    film.innerHTML = stageHTML(L);
    host.innerHTML = "";
    host.appendChild(film);
    const $ = (s) => film.querySelector(s);
    const $$ = (s) => [...film.querySelectorAll(s)];

    const tl = gsap.timeline({ paused: true });
    const sfx = [];
    const cue = (kind, t, o = {}) => sfx.push({ kind, t, id: o.id || kind, ...o });
    const fromTo = (tg, from, to, pos) => {
      const t2 = { ...to, immediateRender: false };
      for (const k in from) if (!(k in t2)) t2[k] = from[k];
      return tl.fromTo(tg, from, t2, pos);
    };

    // ---- reel: 每個畫布在每個時間點畫哪個片段的哪一格 ----
    const reel = []; // {cv, clip, f0, f1, t0, t1}
    const seg = (cv, clip, f0, f1, t0, t1) => reel.push({ cv, clip, f0, f1, t0, t1 });
    // 依序接片段: parts = [[clip, f0, f1], ...], 以同一個速度鋪滿 t0~t1
    const chain = (cv, parts, t0, t1) => {
      const n = parts.reduce((a, p) => a + (p[2] - p[1]), 0);
      let t = t0;
      for (const p of parts) { const d = ((p[2] - p[1]) / n) * (t1 - t0); seg(cv, p[0], p[1], p[2], t, t + d); t += d; }
    };
    const canv = {}; for (const c of $$("canvas")) canv[c.id.slice(2)] = c;
    const pending = new Set();
    const imgCache = root.__VID_IMG || (root.__VID_IMG = new Map());
    const vids = {};
    const want = {};
    function drawFrame(cvId, clipId, f) {
      const cv = canv[cvId], c = CLIPS[clipId];
      f = Math.max(0, Math.min(c.n - 1, Math.floor(f)));
      const key = clipId + ":" + f;
      if (want[cvId] === key) return;
      want[cvId] = key;
      const ctx = cv.getContext("2d");
      if (isRender()) {
        const src = `../${c.dir}/f${pad4(c.first + f)}.jpg`;
        let im = imgCache.get(src);
        if (!im) { im = new Image(); im.src = src; imgCache.set(src, im); if (imgCache.size > 300) imgCache.delete(imgCache.keys().next().value); }
        const paint = () => { if (want[cvId] === key) ctx.drawImage(im, 0, 0, cv.width, cv.height); };
        if (im.complete && im.naturalWidth) paint();
        else pending.add(new Promise((r) => { im.addEventListener("load", () => { paint(); r(); }, { once: true }); im.addEventListener("error", r, { once: true }); }));
      } else {
        let v = vids[cvId + clipId];
        if (!v) {
          v = vids[cvId + clipId] = document.createElement("video");
          v.muted = true; v.playsInline = true; v.preload = "auto"; Promise.resolve(BLOB[clipId]).then((u) => { v.src = u; });
          v.addEventListener("seeked", () => { if (want[cvId] && want[cvId].startsWith(clipId + ":")) ctx.drawImage(v, 0, 0, cv.width, cv.height); });
          v.addEventListener("loadedmetadata", () => { v.currentTime = v._t || 0; });
        }
        v._t = (f + 0.5) / 30;
        if (v.readyState >= 1) v.currentTime = v._t;
      }
    }
    // 鏡頭: 片段座標 (x,y) 放在畫面中央、放大 s 倍; 主畫面夾住不露邊
    const cams = { A: { x: 140, y: 600, s: 1.9 }, P: { x: 255, y: 575, s: 2.2 }, L: { x: 122, y: 26, s: 1.8 } };
    const camEl = { A: $("#camA"), P: $("#camP"), L: $("#camL") };
    const viewSize = { A: [1280, 720], P: [360, 360], L: [420, 420] };
    function applyCam(id) {
      const c = cams[id], [vw, vh] = viewSize[id];
      let tx = vw / 2 - c.x * c.s, ty = vh / 2 - c.y * c.s;
      if (id === "A") { tx = Math.min(0, Math.max(vw - 1280 * c.s, tx)); ty = Math.min(0, Math.max(vh - 720 * c.s, ty)); }
      camEl[id].style.transform = `translate(${tx}px,${ty}px) scale(${c.s})`;
    }
    function drawAll() {
      const t = tl.time();
      const done = new Set();
      for (let i = reel.length - 1; i >= 0; i--) {
        const r = reel[i];
        if (done.has(r.cv) || t < r.t0 || t >= r.t1) continue;
        done.add(r.cv);
        drawFrame(r.cv, r.clip, r.f0 + ((r.f1 - r.f0) * (t - r.t0)) / (r.t1 - r.t0));
      }
      for (const id in cams) applyCam(id);
    }

    // ---- 初始狀態: 只有實機畫面 A 可見 ----
    const hideAll = ["#anger", "#anger2", "#anger3", "#angerP", "#burst1", "#burst2", "#ring1", "#ring2", "#hudbox", "#tint", "#vign", "#speed", "#rgbC", "#rgbM",
      "#pip", "#loupe", "#loupeLine", "#grid", "#cards", "#k7A", "#k7B", "#k7C", "#k7D", "#flash", "#wipe", "#barT", "#barB",
      "#k8A", "#k8P", "#k8B", "#c1", "#c1x", "#c3", "#c4", "#c5", "#c6", "#c7"];
    // 隱藏狀態先寫進 inline style: 時間軸回到 0 時會還原成這個起始值
    for (const el of hideAll.map($)) { el.style.opacity = "0"; el.style.visibility = "hidden"; }
    tl.set(hideAll.map($), { autoAlpha: 0 }, 0);
    tl.set($("#camA"), { autoAlpha: 1, filter: "none" }, 0);
    tl.set($("#camWrap"), { x: 0, y: 0, scale: 1 }, 0);
    tl.set($("#shake"), { x: 0, y: 0 }, 0);
    const capOut = (el, t) => tl.to(el, { autoAlpha: 0, duration: 0.15 }, t - 0.15);
    const shake = (t, amp = 10, n = 6) => tl.to($("#shake"), {
      keyframes: Array.from({ length: n }, (_, i) => ({ x: (i % 2 ? -1 : 1) * amp * (1 - i / n), y: ((i % 3) - 1) * amp * 0.5 * (1 - i / n), duration: 0.035 })).concat([{ x: 0, y: 0, duration: 0.035 }]),
    }, t);

    // ===== K1 · 開場: 角色往前走, 跳不上平台 =====
    {
      const s = starts.k1, e = s + durs.k1;
      chain("A", [["l1a", 18, 78]], s, e);
      const c1 = $("#c1"), chs = $$("#c1m .ch");
      // 從角色特寫慢慢拉遠, 露出高台和旗子; 字幕打字機
      tl.set(cams.A, { x: 140, y: 600, s: 1.9 }, 0);
      tl.to(cams.A, { x: 640, y: 360, s: 1, duration: 1.6, ease: "power2.inOut" }, s + 0.15);
      tl.set(c1, { autoAlpha: 1, y: 0, scale: 1 }, s + 0.3);
      tl.set(chs, { autoAlpha: 0 }, s + 0.001);
      chs.forEach((c, i) => tl.set(c, { autoAlpha: 1 }, s + 0.3 + i * 0.07));
      cue("type", s + 0.35);
      [["jump", 0.633], ["land", 1.367], ["jump", 1.433]].forEach(([g, d]) => cue(g, s + d));   // 遊戲音效事件 (錄影第 37、59、61 格)
    }

    // ===== K2 · 跳不上去: 特寫一直跳, 生氣符號, 字幕延伸 =====
    {
      const s = starts.k2, e = s + durs.k2;
      const ang = [$("#anger"), $("#anger2"), $("#anger3")];
      const c1 = $("#c1"), xs = $$("#c1x .ch");
      const jumpParts = [["l1a", 78, 153]];
      chain("A", jumpParts, s, e);
      tl.set(xs, { autoAlpha: 0 }, s);
      // 延伸字一出現整句會變長: 先顯示延伸段 (透明), 句子從原本置中的位置滑到新的置中位置
      const c1xEl = $("#c1x");
      c1xEl.style.display = "inline-block"; const xw = c1xEl.offsetWidth; c1xEl.style.display = "none";
      const tx = s + 0.4;
      tl.set(c1xEl, { display: "inline-block" }, s);
      tl.set($("#c1m"), { x: xw / 2 }, s);
      tl.to($("#c1m"), { x: 0, duration: 0.3, ease: "power2.inOut" }, tx - 0.3);
      tl.set(c1xEl, { display: "none" }, e);
      // a: 直接切到特寫, 生氣符號跳動, 字幕延伸後整句抖
      tl.set(cams.A, { x: 255, y: 590, s: 3 }, s);
      fromTo(ang[0], { autoAlpha: 1, scale: 0 }, { scale: 1, duration: 0.2, ease: "back.out(3)" }, s + 0.35);
      tl.to(ang[0], { scale: 1.3, duration: 0.13, yoyo: true, repeat: 11, ease: "sine.inOut" }, s + 0.55);
      tl.set($("#c1x"), { autoAlpha: 1 }, s + 0.4);
      xs.forEach((c, i) => tl.set(c, { autoAlpha: 1 }, s + 0.4 + i * 0.08));
      tl.to(c1, { y: -20, duration: 0.5, ease: "power2.out" }, s + 0.4);
      tl.to(c1, { x: 10, duration: 0.045, yoyo: true, repeat: 9 }, s + 1.45);
      cue("zoom", s);
      cue("anger", s + 0.35);
      [["land", 0.167], ["jump", 0.233], ["land", 0.967], ["jump", 1.033], ["land", 1.767], ["jump", 1.833]].forEach(([g, d]) => cue(g, s + d));   // 遊戲音效事件 (錄影第 83~133 格)
      tl.to(ang.concat([$("#angerP")]), { autoAlpha: 0, duration: 0.15 }, e - 0.15);
      capOut(c1, e);
    }

    // ===== K3 · 去死一死: 角色跳坑 =====
    {
      const s = starts.k3, e = s + durs.k3;
      const c3 = $("#c3"), chs = $$("#c3 .ch");
      // 鏡頭跟著角色走到坑邊, 掉下去時慢動作 + 暗角
      seg("A", "l1a", 300, 372, s, s + 1.8);
      seg("A", "l1a", 372, 392, s + 1.8, e);
      tl.set(cams.A, { x: 330, y: 560, s: 1.8 }, s);
      tl.to(cams.A, { x: 690, y: 600, duration: 1.8, ease: "power1.inOut" }, s + 0.01);
      tl.to(cams.A, { s: 2.4, duration: 1.2, ease: "power2.out" }, s + 1.8);
      fromTo($("#vign"), { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.6 }, s + 1.8);
      tl.set(c3, { autoAlpha: 1 }, s + 0.2);
      fromTo(chs, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.01, stagger: 0.05 }, s + 0.2);
      tl.to($("#vign"), { autoAlpha: 0, duration: 0.15 }, e - 0.15);
      cue("fall", s + 1.9);
      cue("cap", s + 0.2); cue("death", s + 1.98);   // 死亡事件在錄影第 375 格 (慢動作段)
      capOut(c3, e);
    }

    // ===== K4 · 切入正題: 強烈轉場, 踩著上一代的頭一路到終點 =====
    {
      const s = starts.k4, e = s + durs.k4;
      // 只留關鍵: 踩第一次頭上低台 → 踩第二次頭上高台 → 碰旗
      const k4parts = [["l1b", 32, 80], ["l1b", 230, 268], ["l1b", 296, 320]];
      chain("A", k4parts, s, e);
      // 兩次踩頭的時間 (片段第 56、241 格)
      const n = 48 + 38 + 24, tA = s + ((56 - 32) / n) * (e - s), tB = s + ((48 + 241 - 230) / n) * (e - s);
      const c4 = $("#c4"), a = $("#c4a"), b = $("#c4b");
      // 片段第 f 格在片中的秒數; 遊戲音效事件 (跳、落地、碰旗) 照錄影時記下的格數放
      const k4t = (f) => { let acc = 0; for (const [, f0, f1] of k4parts) { if (f >= f0 && f < f1) return s + ((acc + f - f0) / n) * (e - s); acc += f1 - f0; } return null; };
      [["jump", 36], ["jump", 59], ["land", 74], ["jump", 244], ["land", 259], ["clear", 317]].forEach(([g, f]) => { const t = k4t(f); if (t != null) cue(g, t); });
      tl.set(cams.A, { x: 640, y: 360, s: 1 }, s);
      const stars = () => [[$("#burst1"), tA], [$("#burst2"), tB]].forEach(([el, t]) => {
        fromTo(el, { autoAlpha: 1, scale: 0, rotation: -30 }, { scale: 1.2, rotation: 0, duration: 0.2, ease: "back.out(3)" }, t);
        tl.to(el, { autoAlpha: 0, scale: 0.6, duration: 0.2 }, t + 0.4);
      });
      // a: 白閃 + 字幕放大砸下 + 大震, 兩側速度線, 踩頭時爆星
      fromTo($("#flash"), { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.45, ease: "power2.out" }, s);
      fromTo(c4, { autoAlpha: 1, scale: 2.6, y: 0 }, { scale: 1, duration: 0.22, ease: "power4.in" }, s + 0.05);
      shake(s + 0.27, 16, 8);
      tl.set($("#speed"), { backgroundPositionX: "0px" }, s);
      fromTo($("#speed"), { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.3 }, s + 0.3);
      tl.to($("#speed"), { backgroundPositionX: "-640px", duration: e - s - 0.3, ease: "none" }, s + 0.3);
      tl.to(c4, { y: -190, scale: 0.6, duration: 0.4, ease: "power2.inOut" }, s + 0.9);
      stars();
      tl.to($("#speed"), { autoAlpha: 0, duration: 0.15 }, e - 0.15);
      cue("slam", s);
      cue("stomp", tA, { id: "stomp1" }); cue("stomp", tB, { id: "stomp2" });
      capOut(c4, e);
    }

    // ===== K5 · 3 條命: 過關回放, 鏡頭推向左上的第幾代 =====
    {
      const s = starts.k5, e = s + durs.k5;
      chain("A", [["l1b", 322, 427]], s, e);
      const c5 = $("#c5");
      tl.set(cams.A, { x: 640, y: 360, s: 1 }, s);
      // 全景回放, 1.1 秒後甩鏡 (模糊) 到 HUD
      tl.to(cams.A, { x: 120, y: 26, s: 3.6, duration: 0.35, ease: "power3.in" }, s + 1.1);
      tl.to($("#camA"), { keyframes: [{ filter: "blur(6px)", duration: 0.25 }, { filter: "blur(0px)", duration: 0.15 }] }, s + 1.1);
      fromTo($("#hudbox"), { autoAlpha: 1, scale: 1.4 }, { scale: 1, duration: 0.25, ease: "back.out(2)" }, s + 1.5);
      fromTo(c5, { autoAlpha: 1, scale: 0.4 }, { scale: 1, duration: 0.35, ease: "back.out(2.4)" }, s + 1.55);
      tl.set($("#camA"), { filter: "none" }, e);
      cue("whip", s + 1.1);
      cue("hud", s + 1.5);
      tl.to($("#hudbox"), { autoAlpha: 0, duration: 0.12 }, e - 0.12);
      capOut(c5, e);
    }

    // ===== K6 · 合作解謎: 快速剪各種解謎片段 =====
    {
      const s = starts.k6, e = s + durs.k6;
      const c6 = $("#c6"), chs = $$("#c6 .ch");
      const parts = [["gate", 0, 90], ["lift", 30, 120], ["hook", 10, 91], ["seesaw", 55, 112]];
      tl.set(cams.A, { x: 640, y: 360, s: 1 }, s);
      // a: 全螢幕快切, 每段 1.25 秒, 切換時白閃
      const step = (e - s) / 4;
      parts.forEach((p, i) => {
        chain("A", [p], s + i * step, s + (i + 1) * step);
        if (i) { fromTo($("#flash"), { autoAlpha: 0.7 }, { autoAlpha: 0, duration: 0.2 }, s + i * step); cue("cut", s + i * step); }
      });
      tl.set(c6, { autoAlpha: 1 }, s + 0.15);
      fromTo(chs, { autoAlpha: 0, scale: 1.8 }, { autoAlpha: 1, scale: 1, duration: 0.18, stagger: 0.04, ease: "back.out(2)" }, s + 0.15);
      cue("cut", s); cue("cap", s + 0.15);
      capOut(c6, e);
    }

    // ===== K7 · 未來計畫: 非遊戲畫面的戰鬥示意 (每個方案一段小動畫) =====
    {
      const s = starts.k7, e = s + durs.k7;
      const c7 = $("#c7"), chs = $$("#c7 .ch");
      const box = $("#k7B");
      const q = (id) => box.querySelector("#" + id);
      const ini = (el, v) => tl.set(el, v, s);
      tl.set($("#camA"), { autoAlpha: 0 }, s + 0.2);
      fromTo(box, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.2 }, s);
      const draw = (el, t, d = 0.4) => { ini(el, { strokeDashoffset: 1 }); tl.to(el, { strokeDashoffset: 0, duration: d, ease: "power2.out" }, t); };
      const popIn = (el, t, from = 0) => fromTo(el, { autoAlpha: 1, scale: from, transformOrigin: "50% 50%" }, { scale: 1, duration: 0.25, ease: "back.out(2.6)" }, t);
      const note = $("#k7nB");
      ini(note, { autoAlpha: 0 });
      // 前一代沿回放軌跡衝過去撞一下 (HIT, 血條掉一半), 本尊照同一路線跳更高補一腳 (COMBO ×2)
      ini([q("k7bf"), q("k7bh1"), q("k7bb"), q("k7bk")], { autoAlpha: 0 });
      ini(q("k7hp"), { scaleX: 1, transformOrigin: "0% 50%" });
      ini([q("k7bg2"), q("k7bj")], { x: 0, y: 0, rotation: 0 });
      ini(q("k7bs"), { scaleY: 1, scaleX: 1, transformOrigin: "50% 100%" });
      draw(q("k7trail"), s + 0.15, 0.5);
      tl.to(q("k7bg2"), { keyframes: [{ x: 270, duration: 0.25, ease: "none" }, { x: 360, y: -110, duration: 0.15, ease: "power1.out" }, { x: 450, y: 0, duration: 0.15, ease: "power1.in" }, { x: 640, duration: 0.18, ease: "power2.in" }] }, s + 0.25);
      const h1 = s + 0.98;
      fromTo(q("k7bf"), { autoAlpha: 0.8 }, { autoAlpha: 0, duration: 0.25 }, h1);
      tl.to(q("k7hp"), { scaleX: 0.5, duration: 0.2, ease: "power2.out" }, h1);
      tl.to(q("k7bg2"), { x: 560, y: -40, rotation: -20, duration: 0.25, ease: "power2.out" }, h1);
      tl.to(q("k7bg2"), { y: 0, rotation: 0, duration: 0.2, ease: "bounce.out" }, h1 + 0.25);
      popIn(q("k7bh1"), h1);
      tl.to(q("k7bh1"), { autoAlpha: 0, y: -30, duration: 0.25 }, h1 + 0.5);
      tl.to(q("k7bs"), { scaleX: 1.1, scaleY: 0.88, duration: 0.08, yoyo: true, repeat: 1 }, h1);
      tl.to(q("k7bj"), { keyframes: [{ x: 270, duration: 0.25, ease: "none" }, { x: 450, y: -230, duration: 0.25, ease: "power2.out" }, { x: 760, y: -150, duration: 0.2, ease: "power1.in" }] }, s + 1.15);
      const h2 = s + 1.85;
      fromTo(q("k7bf"), { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.3 }, h2);
      tl.to(q("k7hp"), { scaleX: 0.001, duration: 0.2 }, h2);
      tl.to(q("k7bs"), { scaleY: 0.4, scaleX: 1.35, duration: 0.12, ease: "power3.out" }, h2);
      tl.to(q("k7bj"), { y: -80, duration: 0.25, ease: "power2.out" }, h2);
      popIn(q("k7bb"), h2);
      tl.to(q("k7bb"), { rotation: 30, autoAlpha: 0, duration: 0.4 }, h2 + 0.3);
      fromTo(q("k7bk"), { autoAlpha: 1, scale: 2.4, rotation: -8, transformOrigin: "50% 50%" }, { scale: 1, rotation: -4, duration: 0.22, ease: "power4.in" }, h2 + 0.15);
      shake(h2 + 0.37, 10, 6);
      popIn(note, s + 0.35, 0.3);
      cue("hit", h1, { id: "k7hit1" }); cue("hit", h2, { id: "k7hit2" }); cue("combo", h2 + 0.37);
      cue("dash", s + 0.25); cue("note", s + 0.35); cue("k7jump", s + 1.15); cue("cap", s + 0.3);
      tl.set(c7, { autoAlpha: 1 }, s + 0.3);
      fromTo(chs, { autoAlpha: 0, y: 20 }, { autoAlpha: 1, y: 0, duration: 0.15, stagger: 0.035 }, s + 0.3);
      tl.set(box, { autoAlpha: 0 }, e);
      tl.set($("#camA"), { autoAlpha: 1 }, e);
      capOut(c7, e);
    }

    // ===== K8 · 收尾: 全部通關畫面變暗, 兩個大標籤一前一後蓋章 (不放字幕) =====
    {
      const s = starts.k8, e = s + durs.k8;
      chain("A", [["ending", 20, 140]], s, e);
      tl.set(cams.A, { x: 640, y: 360, s: 1 }, s);
      tl.to(cams.A, { s: 1.12, x: 640, y: 340, duration: e - s - 0.01, ease: "none" }, s + 0.01);
      tl.to($("#camA"), { filter: "brightness(.45)", duration: 0.4 }, s + 0.3);
      fromTo($("#k8A"), { autoAlpha: 1, scale: 3, rotation: -12 }, { scale: 1, rotation: -3, duration: 0.22, ease: "power4.in" }, s + 0.6);
      shake(s + 0.82, 12, 6);
      fromTo($("#k8P"), { autoAlpha: 1, scale: 0 }, { scale: 1, duration: 0.18, ease: "back.out(3)" }, s + 0.98);
      fromTo($("#k8B"), { autoAlpha: 1, scale: 3, rotation: 12 }, { scale: 1, rotation: 3, duration: 0.22, ease: "power4.in" }, s + 1.12);
      shake(s + 1.34, 12, 6);
      tl.to([$("#k8A"), $("#k8B")], { scale: 1.05, duration: 0.5, yoyo: true, repeat: 1, ease: "sine.inOut" }, s + 2.0);
      cue("stamp", s + 0.82, { id: "stamp1" }); cue("stamp", s + 1.34, { id: "stamp2" });
      cue("dim", s + 0.3); cue("pulse", s + 2.0);
    }

    tl.set({}, {}, total);
    tl.timeScale(SPEED).paused(false);
    const out = gsap.timeline({ paused: true, onUpdate: drawAll });
    out.add(tl, 0);
    drawAll();
    const fast = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v / SPEED]));
    return {
      tl: out, total: total / SPEED, starts: fast(starts), durs: fast(durs), film,
      sfx: sfx.map((c) => ({ ...c, t: c.t / SPEED })),
      // 渲染工具每次 seek 後等這個: 畫格圖片載完並畫上畫布
      settle: async () => { drawAll(); while (pending.size) { const ps = [...pending]; pending.clear(); await Promise.all(ps); } },
    };
  }

  root.VID = { FORMATS, size, KEYFRAMES, OPTIONS, SPEED, CSS, FONT_SAMPLE, fontsFor, build };
})(window);
