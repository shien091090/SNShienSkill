// film.js — the whole video as one GSAP timeline. Contract used by index.html (review page),
// test.html (render harness), tools/renderfilm.mjs and tools/sfxcues.mjs. Every DOM query is scoped
// to `host`, so one page can hold many films (the review page builds one per option preview).
//
// 馬戲團 (WebGame_DungeonZoo) 30 秒介紹 (PVD 網站 trailer, 1280×720, 60fps)。
// 實機畫面走「片段」: 兩個畫面框 L / R, 各有一張畫布; reel 記錄每段時間畫哪個片段的第幾格 (60fps 格號)。
// 審閱頁畫 frames/<id>.jpg 的圖片格 (640 寬 30fps, tools/frames.mjs), 渲染 (test.html 設 VID_RENDER) 讀 ../media/<id>.mp4 (2 倍解析度);
// 每次 seek 後 FILM.settle() 等那一格畫上畫布。片段格數與主角位置在 clipdata.js (tools/clips.mjs 產生)。
(function (root) {
  const FORMATS = {
    wide: { W: 1280, H: 720 }, // PVD 網站試玩頁「30 秒介紹」彈窗
  };
  const fmtOf = (picks) => (FORMATS[picks && picks.fmt] ? picks.fmt : Object.keys(FORMATS)[0]);
  const size = (picks) => FORMATS[fmtOf(picks)];

  const KEYFRAMES = [
    ["k1", 0, 2.0],
    ["k2", 2.0, 1.2],
    ["k3", 3.2, 1.0],
    // 4~10 秒快閃: 拿掉「提升能力」與兩個「抓更多的怪」, 剩 7 個畫面平分 6 秒 (每個約 0.86 秒)
    ["k4", 4.2, 18 / 7],
    ["k5", 6.77, 18 / 7],
    ["k6", 9.34, 6 / 7],
    ["k7", 10.2, 3.0],
    ["k7b", 13.2, 1.4], // 鏡頭跟著最後一隻怪物衝進帳篷入口, 黑畫面接猴子小劇場 (原 K8、K9 已移除)
    ["k10", 14.6, 4.5],
    ["k12", 19.1, 2.0], // 安排節目移到大亂鬥前面
    ["k11", 21.1, 3.4], // 拉長: 最後觀眾冒出「我要看到血流成河!」
    ["k14", 24.5, 2.8], // 原 K13 冷場、K14 移除, 改成熱度條特寫 → 拉回失控畫面
    ["k15", 27.3, 3.0], // 定格在失控畫面, 布幕拉上後停住, 兩大標籤打上來
  ].map(([id, o, d]) => ({ id, o, d }));

  // 每幀 a/b/c(/d) 方案; 沒選的當 a。k10clap 是 K10 裡觀眾拍手那一小段的方案 (不是獨立的幀)
  const OPTIONS = Object.fromEntries(KEYFRAMES.filter((k) => k.id !== "k7b").map((k) => [k.id, ["a", "b", "c"]]));
  OPTIONS.k10clap = ["a", "b", "c", "d"];
  OPTIONS.k11 = ["a", "b", "c", "d"];
  OPTIONS.k14 = ["a", "b", "c", "d"];
  OPTIONS.k14cap = ["a", "b", "c", "d"]; // K14 字幕「喔不! 要失控啦~~~」的動態
  const DUR = (pick) => ({});
  const SPEED = 1;

  const NAVY = "#1b1633", RED = "#e2404f", GOLD = "#ffc93c", TEAL = "#1f9e74";
  const CSS = `
    .vid { position:absolute; inset:0; overflow:hidden; background:${NAVY}; color:#fff; font-family:"Noto Sans TC",sans-serif; }
    .vid .abs { position:absolute; }
    .vid .ov { position:absolute; inset:0; pointer-events:none; }
    .vid #shake { position:absolute; inset:0; }
    .vid #world { position:absolute; left:0; top:0; width:1280px; height:720px; perspective:1400px; }
    .vid .pan { position:absolute; overflow:hidden; background:#000; }
    .vid .cam { position:absolute; left:0; top:0; width:1280px; height:720px; transform-origin:0 0; }
    .vid canvas { display:block; width:100%; height:100%; }
    .vid .shade { position:absolute; inset:0; background:#000; }
    .vid .bd { position:absolute; inset:0; border:6px solid #fff; border-radius:inherit; box-shadow:inset 0 0 0 2px rgba(0,0,0,.25); }
    .vid #divider { position:absolute; left:636px; top:0; width:8px; height:720px; background:#fff; box-shadow:0 0 18px rgba(0,0,0,.5); transform-origin:50% 50%; }
    .vid #band { position:absolute; left:0; top:-40px; width:260px; height:800px; background:${GOLD}; box-shadow:0 0 0 14px ${RED}; }
    .vid #fog { background:radial-gradient(ellipse at 50% 50%, rgba(255,244,220,.55), rgba(40,30,80,.55)); }
    .vid .tag { position:absolute; left:0; top:0; font-weight:900; font-size:104px; line-height:1; padding:16px 44px 22px; border-radius:30px;
      border:8px solid #fff; color:#fff; white-space:nowrap; box-shadow:0 12px 0 rgba(0,0,0,.35), 0 20px 40px rgba(0,0,0,.35);
      -webkit-text-stroke:10px ${NAVY}; paint-order:stroke fill; }
    .vid #tagL { background:${TEAL}; }
    .vid #tagR { background:${RED}; }
    .vid .cap { position:absolute; left:0; right:0; bottom:54px; text-align:center; font-weight:900; font-size:60px; line-height:1.15;
      color:#fff; -webkit-text-stroke:12px ${NAVY}; paint-order:stroke fill; text-shadow:0 6px 0 rgba(0,0,0,.35); white-space:nowrap; }
    .vid .cap .y { color:${GOLD}; }
    .vid .ib { display:inline-block; }
    .vid .stk { position:absolute; font-weight:900; color:${NAVY}; background:${GOLD}; padding:6px 26px 10px; border-radius:12px; font-size:58px;
      border:5px solid ${NAVY}; box-shadow:0 7px 0 rgba(0,0,0,.35); white-space:nowrap; -webkit-text-stroke:0; }
    .vid .k10 svg { position:absolute; left:0; top:0; }
  `;

  const CAPS = {
    c4: ["探索", "開寶箱", "打怪"],
    c5: ["抓怪、", "抓怪、", "抓更多的怪"],
    c7a: "奴役", c7b: "帶領", c7c: "他們去表演", c7x: "欸?不對!",
    c11a: "讓怪物們大亂鬥!", c11b: "打得越激烈觀眾越愛看",
    c11q: "我要看到血流成河!",
    c12: "安排表演節目", c14a: "喔不!", c14b: "要失控啦~~~",
  };
  const TAGS = { L: "搜打撤", R: "自動經營" };
  const FONT_SAMPLE = JSON.stringify(CAPS).replace(/[\[\]{}":a-z0-9]/g, "") + TAGS.L + TAGS.R + "!?、,…zZ+✓WARNING";
  const fontsFor = (picks) => ['900 60px "Noto Sans TC"', '700 40px "Noto Sans TC"'];

  const isRender = () => !!root.VID_RENDER;
  // 審閱頁的遊戲畫面只有 640 寬, 畫布 1280 就夠
  const CW = () => (isRender() ? 2560 : 1280), CH = () => (isRender() ? 1440 : 720);
  // 片段上要蓋掉的遊戲提示: [x, y, w, h, 往左取幾 px 的地板蓋上去] (1280×720 座標); 從同一張畫面複製, 顏色才會一模一樣
  const PATCH = { im: [[548, 645, 190, 62, 230]] };

  // 審閱頁的遊戲畫面: 不用 <video> (跳格慢、同時太多個瀏覽器會停掉 → 卡頓、整段不見), 改用 tools/frames.mjs
  // 預先轉好的 JPEG 格 (640 寬 30fps, 只有影片用到的格)。開頁整包下載, 要畫時才解碼, 解好的格所有播放器共用
  const FD = root.FRAMEDATA || {};
  const clipIds = Object.keys(FD);
  const PACK = {}, BMP = new Map(), DEC = new Map(), WAIT = new Set();
  const BMP_MAX = 260; // 解好的格最多留幾張 (640×360 一張約 0.9MB)
  let clipsLoaded = 0;
  const clipsReady = isRender() ? Promise.resolve() : Promise.all(clipIds.map((id) => fetch(`frames/${id}.jpg`)
    .then((r) => r.arrayBuffer()).then((ab) => { PACK[id] = ab; }).catch(() => {}).then(() => { clipsLoaded++; })));
  root.VID_CLIPS = { ready: clipsReady, progress: () => [clipsLoaded, clipIds.length] };
  // 片段 id 的第 j 格 (30fps) 最接近且有轉出來的格號
  function nearJ(id, j) {
    const ix = FD[id];
    if (!ix || !ix.length) return -1;
    let lo = 0, hi = ix.length - 1;
    while (lo < hi) { const m = (lo + hi + 1) >> 1; if (ix[m][0] <= j) lo = m; else hi = m - 1; }
    return lo;
  }
  // 拿解好的格; 沒解好就開始解 (解好後通知 WAIT 裡的播放器重畫), 回傳 null
  function frameBmp(id, k) {
    const key = id + ":" + k;
    const b = BMP.get(key);
    if (b) { BMP.delete(key); BMP.set(key, b); return b; }
    if (!DEC.has(key) && PACK[id]) {
      const [, off, len] = FD[id][k];
      DEC.set(key, createImageBitmap(new Blob([new Uint8Array(PACK[id], off, len)], { type: "image/jpeg" })).then((bm) => {
        BMP.set(key, bm);
        while (BMP.size > BMP_MAX) { const [k0, b0] = BMP.entries().next().value; BMP.delete(k0); b0.close && b0.close(); }
        DEC.delete(key);
        WAIT.forEach((fn) => fn());
        return bm;
      }, () => { DEC.delete(key); return null; }));
    }
    return null;
  }

  // ===== K10 猴子小劇場 (非遊戲畫面) =====
  // 猴子: 原點在腳底中央, 面朝前; 右邊那隻外層用 scale(-1,1) 翻面。表情三組 (N 平常 / S 驚訝 / A 生氣) 用透明度切換
  function monkey(c) {
    return `<g class="${c}"><g class="mBody">
      <path d="M-40,-60 Q-110,-40 -95,-130" fill="none" stroke="#b3601f" stroke-width="12" stroke-linecap="round"/>
      <ellipse cx="0" cy="-62" rx="54" ry="64" fill="#e8873a" stroke="${NAVY}" stroke-width="6"/>
      <ellipse cx="6" cy="-56" rx="32" ry="40" fill="#f6d3a1"/>
      <g class="arm"><path d="M20,-90 Q70,-100 78,-60" fill="none" stroke="${NAVY}" stroke-width="28" stroke-linecap="round"/>
        <path d="M20,-90 Q70,-100 78,-60" fill="none" stroke="#e8873a" stroke-width="18" stroke-linecap="round"/></g>
      <g class="hd"><g transform="translate(0,-160)">
        <circle cx="-66" cy="-6" r="26" fill="#e8873a" stroke="${NAVY}" stroke-width="6"/><circle cx="-66" cy="-6" r="13" fill="#f6d3a1"/>
        <circle cx="66" cy="-6" r="26" fill="#e8873a" stroke="${NAVY}" stroke-width="6"/><circle cx="66" cy="-6" r="13" fill="#f6d3a1"/>
        <circle cx="0" cy="0" r="68" fill="#e8873a" stroke="${NAVY}" stroke-width="6"/>
        <path d="M-50,-6 Q-26,-34 0,-12 Q26,-34 50,-6 Q60,40 0,52 Q-60,40 -50,-6 Z" fill="#f6d3a1"/>
        <ellipse class="fl" cx="0" cy="14" rx="56" ry="40" fill="#ff3b30"/>
        <g class="eyN"><circle class="pu" cx="-20" cy="2" r="8" fill="${NAVY}"/><circle class="pu" cx="20" cy="2" r="8" fill="${NAVY}"/></g>
        <g class="eyS"><circle cx="-21" cy="0" r="15" fill="#fff" stroke="${NAVY}" stroke-width="4"/><circle cx="21" cy="0" r="15" fill="#fff" stroke="${NAVY}" stroke-width="4"/>
          <circle cx="-19" cy="0" r="6" fill="${NAVY}"/><circle cx="23" cy="0" r="6" fill="${NAVY}"/></g>
        <g class="eyA"><path d="M-38,-22 L-8,-8 M38,-22 L8,-8" stroke="${NAVY}" stroke-width="8" stroke-linecap="round"/>
          <circle cx="-20" cy="6" r="7" fill="${NAVY}"/><circle cx="20" cy="6" r="7" fill="${NAVY}"/></g>
        <path class="mN" d="M-16,26 Q0,38 16,26" fill="none" stroke="${NAVY}" stroke-width="6" stroke-linecap="round"/>
        <ellipse class="mS" cx="0" cy="32" rx="10" ry="13" fill="${NAVY}"/>
        <path class="mA" d="M-20,36 L-10,26 L0,36 L10,26 L20,36" fill="none" stroke="${NAVY}" stroke-width="6" stroke-linejoin="round"/>
      </g></g></g></g>`;
  }
  const ANGER = `<g fill="none" stroke="${RED}" stroke-width="9" stroke-linecap="round">
    <path d="M-7,-28 Q-8,-8 -28,-7"/><path d="M7,-28 Q8,-8 28,-7"/><path d="M-7,28 Q-8,8 -28,7"/><path d="M7,28 Q8,8 28,7"/></g>`;
  const MATCH = `<rect x="-26" y="-3" width="52" height="6" rx="3" fill="#f2d39b" stroke="${NAVY}" stroke-width="2"/>
    <circle cx="27" cy="0" r="7" fill="#d23b2c" stroke="${NAVY}" stroke-width="2"/>
    <path d="M30,-4 Q48,-20 40,4 Q50,-2 44,12 Q36,6 30,4 Z" fill="#ffb627"/><path d="M33,-1 Q42,-10 38,4 Z" fill="#fff1a8"/>`;
  const BOOM = `<polygon fill="${GOLD}" stroke="${NAVY}" stroke-width="4" points="0,-34 8,-12 32,-18 14,0 32,18 8,12 0,34 -8,12 -32,18 -14,0 -32,-18 -8,-12"/>`;
  const BANG = `<text x="0" y="0" text-anchor="middle" dominant-baseline="middle" font-size="84" font-weight="900" fill="${GOLD}" stroke="${NAVY}" stroke-width="10" paint-order="stroke fill">!</text>`;
  function theater(U) {
    const spot = (cx, w) => `<polygon points="${cx - 26},-10 ${cx + 26},-10 ${cx + w},560 ${cx - w},560" fill="url(#${U}-sp)"/>
      <ellipse cx="${cx}" cy="560" rx="${w}" ry="34" fill="#fff6d0" opacity=".35"/>`;
    // 觀眾: 身體、頭、兩隻手臂 (從肩膀轉, 拍手 = 兩手往中間轉到碰在一起); 頭上預留各方案用的裝飾 (拍手衝擊線、「啪!」、愛心)
    const arm = (c, sx, sy, hx, hy) => `<g class="${c}" data-o="${sx} ${sy}"><path d="M${sx},${sy} L${hx},${hy}" stroke="#55468c" stroke-width="22" stroke-linecap="round"/>
      <path d="M${sx},${sy} L${hx},${hy}" stroke="#2c2350" stroke-width="16" stroke-linecap="round"/><circle cx="${hx}" cy="${hy}" r="15" fill="#f6d3a1" stroke="#2c2350" stroke-width="3"/></g>`;
    const HEART = `<path d="M0,8 C-14,-4 -12,-18 -2,-16 C0,-15 0,-13 0,-12 C0,-13 0,-15 2,-16 C12,-18 14,-4 0,8 Z" fill="#ff5b7a" stroke="${NAVY}" stroke-width="3"/>`;
    const people = Array.from({ length: 12 }, (_, i) => {
      const x = 60 + i * 106 + (i % 2 ? 14 : -8), y = 700 + (i % 3) * 8;
      return `<g class="pp" data-i="${i}"><g class="pb"><ellipse cx="${x}" cy="${y + 40}" rx="56" ry="46" fill="#2c2350" stroke="#55468c" stroke-width="3"/>
        ${arm("al", x - 36, y + 8, x - 24, y - 94)}${arm("ar", x + 36, y + 8, x + 24, y - 94)}
        <circle cx="${x}" cy="${y - 30}" r="30" fill="#2c2350" stroke="#55468c" stroke-width="3"/></g>
        <g class="ci" transform="translate(${x},${y - 112})" stroke="#fff6d0" stroke-width="7" stroke-linecap="round"><path d="M0,-16 L0,-42"/><path d="M-16,-8 L-36,-24"/><path d="M16,-8 L36,-24"/></g>
        <g transform="translate(${x},${y - 170})"><text class="pa" x="0" y="0" text-anchor="middle" font-size="58" font-weight="900" fill="${GOLD}" stroke="${NAVY}" stroke-width="10" paint-order="stroke fill">啪!</text></g>
        <g transform="translate(${x + (i % 2 ? 16 : -16)},${y - 130})"><g class="ht"><g transform="scale(2)">${HEART}</g></g></g></g>`;
    }).join("");
    const confetti = Array.from({ length: 40 }, (_, i) => `<rect class="cf" x="${(i * 97) % 1280}" y="${-30 - ((i * 53) % 200)}" width="14" height="8" rx="2" fill="${["#ff5d7a", "#ffd24a", "#c6f046", "#5ad1e6", "#ff8fc8", "#b46cff"][i % 6]}"/>`).join("");
    return `<svg viewBox="0 0 1280 720" width="1280" height="720">
      <defs><linearGradient id="${U}-sp" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff8dc" stop-opacity=".75"/><stop offset="1" stop-color="#fff8dc" stop-opacity=".12"/></linearGradient>
        <radialGradient id="${U}-bg" cx=".5" cy=".7" r=".8"><stop offset="0" stop-color="#2a1d4a"/><stop offset="1" stop-color="#07060f"/></radialGradient></defs>
      <g id="${U}-scene"><g class="tcam">
        <rect x="-600" y="-500" width="2480" height="1720" fill="url(#${U}-bg)"/>
        <rect x="-600" y="560" width="2480" height="660" fill="#160f2b"/>
        <path d="M-600,-500 L120,-500 Q90,200 160,620 L-600,620 Z" fill="#7d1624"/><path d="M1880,-500 L1160,-500 Q1190,200 1120,620 L1880,620 Z" fill="#7d1624"/>
        <g class="sp1">${spot(420, 170)}</g><g class="sp2">${spot(860, 170)}</g><g class="sp3">${spot(640, 330)}</g>
        <g transform="translate(420,560)">${monkey("m1")}</g>
        <g transform="translate(860,560) scale(-1,1)">${monkey("m2")}</g>
        <g transform="translate(420,290)"><g class="ex1">${BANG}</g></g>
        <g transform="translate(860,290)"><g class="ex2">${BANG}</g></g>
        <g transform="translate(505,330)"><g class="an1">${ANGER}</g></g>
        <g transform="translate(775,330)"><g class="an2">${ANGER}</g></g>
        ${Array.from({ length: 10 }, (_, i) => `<g class="mt mt${i}">${MATCH}</g>`).join("")}
        ${Array.from({ length: 10 }, (_, i) => `<g class="bm bm${i}">${BOOM}</g>`).join("")}
      </g></g>
      <g class="crowd">${people}</g>
      <g class="cfs">${confetti}</g>
    </svg>`;
  }

  // 集中線 (K6 b): 以 (cx,cy) 為中心
  const raysSVG = (cx, cy, n = 48, inner = 300, col = "#fff", op = 0.55) => `<svg viewBox="0 0 1280 720" width="1280" height="720" class="abs" style="left:0;top:0">${Array.from({ length: n }, (_, i) => {
    const a = (i / n) * Math.PI * 2, b = a + 0.035, r0 = inner + (i % 4) * 40;
    return `<polygon points="${(cx + Math.cos(a) * r0).toFixed(0)},${(cy + Math.sin(a) * r0 * 0.6).toFixed(0)} ${(cx + Math.cos(a) * 1500).toFixed(0)},${(cy + Math.sin(a) * 1500).toFixed(0)} ${(cx + Math.cos(b) * 1500).toFixed(0)},${(cy + Math.sin(b) * 1500).toFixed(0)}" fill="${col}" opacity="${op}"/>`;
  }).join("")}</svg>`;
  const RAYS = raysSVG(640, 560);
  // 鋸齒爆炸形 (K11 c、K14 b)
  const jag = (rx, ry, n, fill, stroke) => `<polygon fill="${fill}" stroke="${stroke}" stroke-width="10" stroke-linejoin="round" points="${Array.from({ length: n * 2 }, (_, i) => {
    const a = (i / (n * 2)) * Math.PI * 2, k = i % 2 ? 0.62 + 0.1 * Math.sin(i * 3.7) : 1;
    return `${(Math.cos(a) * rx * k).toFixed(0)},${(Math.sin(a) * ry * k).toFixed(0)}`;
  }).join(" ")}"/>`;
  const BURST = `<g class="bs">${jag(390, 145, 14, RED, NAVY)}${jag(330, 112, 14, GOLD, "none")}</g>`;
  // K14 失控特效 (各方案一組): shk 衝擊波 / bst 漫畫爆炸 / emb 火星 / flm 火焰邊框
  const FLAME = (x, y, s, r) => `<g transform="translate(${x},${y}) rotate(${r}) scale(${s})"><g class="fl"><path d="M0,0 C-60,-40 -50,-120 -10,-200 C-5,-140 30,-130 25,-180 C70,-110 70,-40 0,0 Z" fill="#ff5a1f"/>
    <path d="M0,0 C-34,-26 -28,-84 -4,-130 C0,-90 22,-84 18,-116 C44,-70 40,-24 0,0 Z" fill="#ffc93c"/></g></g>`;
  const FX14 = `<svg viewBox="0 0 1280 720" width="1280" height="720" class="abs" style="left:0;top:0">
    <g class="shk">${[0, 1, 2].map((i) => `<circle class="rg rg${i}" cx="640" cy="300" r="100" fill="none" stroke="${i === 1 ? GOLD : "#fff"}" stroke-width="${18 - i * 4}"/>`).join("")}</g>
    <g class="bst"><g class="spd">${raysSVG(640, 300, 56, 230, "#fff", 0.7).replace(/<\/?svg[^>]*>/g, "")}</g></g>
    <g class="emb">${Array.from({ length: 36 }, (_, i) => `<circle class="em" cx="${(i * 149) % 1280}" cy="${740 + (i * 37) % 80}" r="${4 + (i % 4) * 2}" fill="${i % 3 ? "#ff7a1f" : GOLD}"/>`).join("")}</g>
    <g class="flm">${Array.from({ length: 11 }, (_, i) => FLAME(i * 128, 730, 0.9 + ((i * 7) % 5) * 0.12, 0)).join("")}
      ${[120, 300, 480, 660].map((y, i) => FLAME(-20, y + 60, 0.7 + (i % 2) * 0.2, 90) + FLAME(1300, y, 0.7 + ((i + 1) % 2) * 0.2, -90)).join("")}</g>
  </svg>`;

  function stageHTML(L, pick, U) {
    const p5 = pick("k5");
    // K5 三段字幕: a 單行接龍 / b 越來越大的三行 / c 貼紙
    let k5 = "";
    if (p5 === "b") {
      k5 = `<div class="cap k5" id="c5_0" style="bottom:auto;top:420px;left:170px;right:auto;font-size:46px">${CAPS.c5[0]}</div>
        <div class="cap k5" id="c5_1" style="bottom:auto;top:472px;left:320px;right:auto;font-size:62px">${CAPS.c5[1]}</div>
        <div class="cap k5 more" id="c5_2" style="bottom:auto;top:540px;left:470px;right:auto;font-size:96px;color:${GOLD};transform-origin:50% 60%">${CAPS.c5[2]}</div>`;
    } else if (p5 === "c") {
      k5 = `<div class="stk k5" id="c5_0" style="left:150px;top:470px">${CAPS.c5[0]}</div>
        <div class="stk k5" id="c5_1" style="left:430px;top:500px;background:#ffe08a">${CAPS.c5[1]}</div>
        <div class="stk k5 more" id="c5_2" style="left:690px;top:540px;background:${RED};color:#fff;font-size:72px;transform-origin:50% 50%">${CAPS.c5[2]}</div>`;
    } else {
      k5 = `<div class="cap" id="c5line"><span class="ib k5" id="c5_0">${CAPS.c5[0]}</span><span class="ib k5" id="c5_1">${CAPS.c5[1]}</span><span class="ib k5 more y" id="c5_2" style="transform-origin:50% 60%">${CAPS.c5[2]}</span></div>`;
    }
    const p4 = pick("k4");
    const c4 = CAPS.c4.map((t, i) => (p4 === "b"
      ? `<div class="cap c4" id="c4_${i}" style="bottom:34px;font-size:104px;-webkit-text-stroke:16px ${NAVY}">${t}</div>`
      : p4 === "c" ? `<div class="stk c4" id="c4_${i}" style="left:56px;top:26px;font-size:54px">${t}</div>`
        : `<div class="cap c4" id="c4_${i}">${t}</div>`)).join("");
    const k7 = pick("k7") === "c"
      ? `<div class="cap" id="c7"><span class="ib" id="c7w" style="position:relative">${CAPS.c7a}<span class="abs" id="c7s" style="left:-6px;right:-6px;top:52%;height:9px;background:#ff3b3b;border-radius:5px;transform-origin:0 50%"></span>
          <span class="abs" id="c7n" style="left:50%;top:-84px;font-size:56px;color:#ff6b78;white-space:nowrap">${CAPS.c7b}<span style="font-size:40px">✓</span></span></span><span class="ib" id="c7r">${CAPS.c7c}</span></div>`
      : `<div class="cap" id="c7"><span class="ib" id="c7w" style="position:relative;width:2.1em;height:1.15em;vertical-align:bottom">
          <span class="abs" id="c7o" style="left:0;top:0;width:100%">${CAPS.c7a}<span class="abs" id="c7s" style="left:-6px;right:-6px;top:52%;height:9px;background:#ff3b3b;border-radius:5px;transform-origin:0 50%"></span></span>
          <span class="abs y" id="c7n" style="left:0;top:0;width:100%">${CAPS.c7b}</span></span><span class="ib" id="c7r">${CAPS.c7c}</span></div>
        <div class="abs" id="c7x" style="left:0;right:0;top:250px;text-align:center"><span class="stk" style="position:relative;font-size:64px;background:#fff">${CAPS.c7x}</span></div>`;
    return `
    <div id="shake">
      <div id="world">
        ${["L", "R"].map((P) => `<div class="pan" id="p${P}"><div class="cam" id="c${P}"><canvas id="cv${P}" width="${CW()}" height="${CH()}"></canvas>
          <div class="abs" id="hf${P}" style="left:404px;top:2px;width:506px;height:56px;border:4px solid #ff3b30;border-radius:12px;box-shadow:0 0 14px #ff3b30, inset 0 0 10px #ff3b30"></div></div><div class="shade" id="sh${P}"></div><div class="bd" id="bd${P}"></div></div>`).join("")}
        <div id="divider"></div>
        <div id="band"></div>
      </div>
      <div class="ov" id="fog"></div>
      <div class="ov" id="rays">${RAYS}</div>
      <div class="ov" id="redv" style="background:radial-gradient(ellipse at 50% 50%, rgba(255,0,0,0) 40%, rgba(255,20,40,.75) 100%)"></div>
      <div class="ov" id="redt" style="background:#ff1a2e;mix-blend-mode:multiply"></div>
      <div class="ov" id="fx14">${FX14}</div>
      <div class="abs" id="frame12" style="left:396px;top:146px;width:520px;height:170px;border:7px solid ${GOLD};border-radius:16px;box-shadow:0 0 0 6px ${NAVY},0 0 30px ${GOLD}"></div>
      <canvas class="ov" id="fin" width="${CW()}" height="${CH()}"></canvas>
      <div class="ov k10" id="th">${theater(U)}</div>
      <svg class="abs" id="pan10" viewBox="0 0 1280 720" width="1280" height="720" style="left:0;top:0">
        <rect width="1280" height="720" fill="#07060f"/>
        <g transform="rotate(-2 330 360)"><rect x="30" y="30" width="600" height="660" fill="#000" stroke="#fff" stroke-width="10"/>
          <svg x="35" y="35" width="590" height="650" viewBox="240 230 360 396" preserveAspectRatio="xMidYMid slice"><use href="#${U}-scene"/></svg></g>
        <g transform="rotate(2 950 360)"><rect x="650" y="30" width="600" height="660" fill="#000" stroke="#fff" stroke-width="10"/>
          <svg x="655" y="35" width="590" height="650" viewBox="680 230 360 396" preserveAspectRatio="xMidYMid slice"><use href="#${U}-scene"/></svg></g>
      </svg>
      <div class="ov" id="black" style="background:#000"></div>
      <div class="ov" id="flash" style="background:#fff"></div>
    </div>
    <div class="abs" id="pls" style="left:0;top:0;width:0;height:0"><div class="abs" id="plsH" style="left:-48px;top:-13px;width:96px;height:26px;background:#fff;border-radius:6px;box-shadow:0 0 18px rgba(0,0,0,.5)"></div>
          <div class="abs" id="plsV" style="left:-13px;top:-48px;width:26px;height:96px;background:#fff;border-radius:6px;box-shadow:0 0 18px rgba(0,0,0,.5)"></div></div>
    <div class="tag" id="tagL">${TAGS.L}</div>
    <div class="tag" id="tagR">${TAGS.R}</div>
    <div class="abs" id="plus" style="left:0;top:0;font-size:110px;font-weight:900;color:${GOLD};-webkit-text-stroke:12px ${NAVY};paint-order:stroke fill">+</div>
    ${c4}
    ${k5}
    ${k7}
    <svg class="abs" id="burst11" viewBox="-400 -150 800 300" width="800" height="300" style="left:240px;top:400px">${BURST}</svg>
    <div class="abs" id="band11" style="left:-40px;right:-40px;top:448px;height:150px;background:${RED};box-shadow:0 0 0 8px ${NAVY};transform:rotate(-4deg)"></div>
    <div class="cap" id="c11"><div id="c11a" style="font-size:108px;line-height:1.1;color:${GOLD};-webkit-text-stroke:18px ${NAVY}">${[...CAPS.c11a].map((ch) => `<span class="ib ch">${ch}</span>`).join("")}</div><div id="c11b">${[...CAPS.c11b].map((ch) => `<span class="ib ch">${ch}</span>`).join("")}</div></div>
    <div class="abs" id="q11" style="left:690px;top:132px"><div style="position:relative;background:#fff;color:${NAVY};font-weight:900;font-size:44px;padding:12px 28px 16px;border-radius:30px;border:6px solid ${NAVY};white-space:nowrap;box-shadow:0 8px 0 rgba(0,0,0,.35)">${CAPS.c11q}
      <svg width="60" height="50" viewBox="0 0 60 50" style="position:absolute;left:118px;top:-44px"><path d="M10,48 L34,2 L46,48" fill="#fff" stroke="${NAVY}" stroke-width="6" stroke-linejoin="round"/><rect x="6" y="44" width="46" height="10" fill="#fff"/></svg></div></div>
    <div class="cap" id="c12">${CAPS.c12}</div>
    <div class="cap" id="c14" style="font-size:72px"><span class="ib" id="c14a" style="color:#ff6b78;position:relative">${[...CAPS.c14a].map((ch) => `<span class="ib ch">${ch}</span>`).join("")}
      <svg class="abs sw" viewBox="-20 -30 40 60" width="34" height="50" style="left:-30px;top:-20px"><path d="M0,-26 C10,-8 16,4 16,12 A16,16 0 0 1 -16,12 C-16,4 -10,-8 0,-26 Z" fill="#8fd3ff" stroke="${NAVY}" stroke-width="4"/></svg>
      <svg class="abs sw" viewBox="-20 -30 40 60" width="26" height="38" style="right:-26px;top:-12px"><path d="M0,-26 C10,-8 16,4 16,12 A16,16 0 0 1 -16,12 C-16,4 -10,-8 0,-26 Z" fill="#8fd3ff" stroke="${NAVY}" stroke-width="4"/></svg></span>&nbsp;<span class="ib" id="c14b">${[...CAPS.c14b].map((ch) => `<span class="ib ch">${ch}</span>`).join("")}</span></div>
    `;
  }

  let UID = 0;
  function build(host, picks = {}) {
    const PREVIEW = !!picks._preview; // 審閱頁的方案預覽
    const pick = (id) => (OPTIONS[id] && OPTIONS[id].includes(picks[id]) ? picks[id] : "a");
    const L = size(picks);
    const over = DUR(pick);
    const starts = {}, durs = {};
    let acc = 0;
    for (const k of KEYFRAMES) { starts[k.id] = acc; durs[k.id] = over[k.id] ?? k.d; acc += durs[k.id]; }
    const total = acc;
    // K10 觀眾拍手那一小段 (審閱頁的方案列用來定位預覽)
    starts.k10clap = starts.k10 + 3.2; durs.k10clap = durs.k10 - 3.2;
    starts.k14cap = starts.k14; durs.k14cap = durs.k14;
    const U = "vf" + ++UID + "x" + Math.floor(Math.random() * 1e6);

    const film = document.createElement("div");
    film.className = "vid";
    film.style.width = L.W + "px";
    film.style.height = L.H + "px";
    film.innerHTML = stageHTML(L, pick, U);
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

    // ---- 兩個畫面框 (L 左 / R 右): 幾何 G、鏡頭 C 都是一般物件, 由時間軸補間, drawAll 套到畫面上 ----
    const CL = root.CLIPDATA || {};
    // wl / wr: 從左 / 右邊裁掉的百分比 (掃過去的轉場用)
    const G = { L: { x: 0, y: 0, w: 640, h: 720, r: 0, wl: 0, wr: 0 }, R: { x: 640, y: 0, w: 640, h: 720, r: 0, wl: 0, wr: 0 } };
    // 鏡頭: 看片段座標 (cx,cy), 放大 z 倍 (以填滿畫框為 1); f = 跟拍主角的比重 (0~1)
    const C = { L: { cx: 640, cy: 400, z: 1, f: 0 }, R: { cx: 640, cy: 400, z: 1, f: 0 } };
    const reel = [];
    // 片段 clip 的 a~b 秒 (片段內時間) 鋪在影片 t0~t1; 後登記的蓋過先登記的
    // 起點提早 0.5ms: 換鏡頭的時間點 (t0 + 0.0001) 剛好落在一格上時, 才不會兩段都沒蓋到而沿用上一個畫面
    const seg = (P, clip, a, b, t0, t1) => reel.push({ P, clip, f0: a * 60, f1: b * 60, t0: t0 - 0.0005, t1 });
    const shot = (P, clip, a, b, t0, t1, cam) => { seg(P, clip, a, b, t0, t1); if (cam) tl.set(C[P], cam, t0); };
    const canv = { L: $("#cvL"), R: $("#cvR") }, camEl = { L: $("#cL"), R: $("#cR") }, panEl = { L: $("#pL"), R: $("#pR") };
    const pending = new Set();
    const PLUS = [634, 330]; // K1「+」位置 (兩個標籤中間)
    // K15 布幕: FIN.t = 謝幕動畫的秒數 (< 0 不畫), 每次畫面更新時用遊戲的畫法畫到 #fin
    const FIN = { t: -1 };
    const finCv = $("#fin"), finCtx = finCv.getContext("2d");
    let finLast = null;
    function drawFin() {
      const t = FIN.t < 0 ? -1 : Math.round(FIN.t * 600) / 600;
      if (t === finLast) return;
      finLast = t;
      finCtx.setTransform(1, 0, 0, 1, 0, 0);
      finCtx.clearRect(0, 0, finCv.width, finCv.height);
      if (t < 0 || !root.FinArt) return;
      finCtx.setTransform(finCv.width / 1280, 0, 0, finCv.height / 720, 0, 0);
      root.FinArt.drawFinale(finCtx, { t });
    }
    const vids = {}, want = {}, hero = { L: null, R: null };
    function seekVid(v, t, paint) {
      v._paint = paint; v._t = t;
      if (v.readyState >= 2 && !v.seeking && Math.abs(v.currentTime - t) < 0.002) { paint(); return; }
      pending.add(new Promise((r) => v._res.push(r)));
      if (v.readyState >= 1) v.currentTime = t;
    }
    // 審閱頁: 畫預先轉好的圖片格 (見檔頭 frameBmp); 還沒解好就先留著上一張, 解好再補畫
    const shown = { L: null, R: null }, wantK = { L: null, R: null };
    function paintBmp(P, clipId, bm) {
      const cv = canv[P], ctx = cv.getContext("2d");
      ctx.drawImage(bm, 0, 0, cv.width, cv.height);
      const k = cv.width / 1280;
      for (const [x, y, w, h, dx] of PATCH[clipId] || []) ctx.drawImage(cv, (x - dx) * k, y * k, w * k, h * k, x * k, y * k, w * k, h * k);
    }
    function liveFrame(P, r, t) {
      const clipId = r.clip, c = CL[clipId] || { n: 1 };
      const f = Math.max(0, Math.min(c.n - 1, r.f0 + ((r.f1 - r.f0) * (t - r.t0)) / (r.t1 - r.t0)));
      hero[P] = c.pos ? c.pos[Math.min(c.pos.length - 1, Math.floor(f) >> 1)] : null;
      const k = nearJ(clipId, Math.round(f / 2));
      if (k < 0) return;
      const key = clipId + ":" + k;
      wantK[P] = key;
      if (shown[P] === key) return;
      const bm = frameBmp(clipId, k);
      if (bm) { paintBmp(P, clipId, bm); shown[P] = key; return; }
      // 還沒解好: 渲染檢查工具 (settle) 要等它; 播放中先留著上一張
      const d = DEC.get(key);
      if (d) pending.add(d);
    }
    // 有格解好時: 每個畫框若還在等那一格就補畫
    const onDecoded = () => {
      for (const P of ["L", "R"]) {
        const key = wantK[P];
        if (!key || shown[P] === key) continue;
        const bm = BMP.get(key);
        if (bm) { paintBmp(P, key.slice(0, key.lastIndexOf(":")), bm); shown[P] = key; }
      }
    };
    if (!isRender()) WAIT.add(onDecoded);
    // 主播放器: 往後 0.8 秒會用到的格先解好
    function prefetch(t) {
      for (const r of reel) {
        if (r.t1 < t || r.t0 > t + 0.8) continue;
        const a = Math.max(t, r.t0), b = Math.min(t + 0.8, r.t1);
        for (let x = a; x <= b; x += 1 / 30) {
          const f = r.f0 + ((r.f1 - r.f0) * (x - r.t0)) / (r.t1 - r.t0), k = nearJ(r.clip, Math.round(f / 2));
          if (k >= 0) frameBmp(r.clip, k);
        }
      }
    }
    function drawFrame(P, clipId, f, slot) {
      const c = CL[clipId] || { n: 1 };
      f = Math.max(0, Math.min(c.n - 1, Math.floor(f)));
      hero[P] = c.pos ? c.pos[Math.min(c.pos.length - 1, f >> 1)] : null;
      const vk = clipId + "#" + (isRender() ? 0 : slot), key = vk + ":" + f;
      if (want[P] === key) return;
      want[P] = key;
      const cv = canv[P], ctx = cv.getContext("2d");
      const v = getVid(vk, clipId);
      // 畫布還停在這段鏡頭就畫 (同段的鄰近格也畫, 不留舊鏡頭的畫面)
      seekVid(v, (f + 0.5) / 60, () => {
        if (!want[P] || !want[P].startsWith(vk + ":")) return;
        ctx.drawImage(v, 0, 0, cv.width, cv.height);
        const k = cv.width / 1280;
        for (const [x, y, w, h, dx] of PATCH[clipId] || []) ctx.drawImage(cv, (x - dx) * k, y * k, w * k, h * k, x * k, y * k, w * k, h * k);
      });
    }
    function getVid(vk, clipId) {
      let v = vids[vk];
      if (!v) {
        v = vids[vk] = document.createElement("video");
        v.muted = true; v.playsInline = true; v.preload = "auto"; v._res = []; v._t = 0;
        const done = () => { const rs = v._res; v._res = []; rs.forEach((r) => r()); };
        v.addEventListener("seeked", () => {
          // 跳到的格子先畫上, 沒對上再跳一次
          if (v._paint) v._paint();
          if (Math.abs(v.currentTime - v._t) > 0.002) { v.currentTime = v._t; return; }
          done();
        });
        v.addEventListener("loadedmetadata", () => { v.currentTime = v._t; });
        v.addEventListener("error", done);
        v.src = `../media/${clipId}.mp4`; // 只有渲染用影片; 審閱頁用圖片格
      }
      return v;
    }
    const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
    function applyPan(P) {
      const g = G[P], c = C[P], el = panEl[P];
      el.style.left = g.x + "px"; el.style.top = g.y + "px"; el.style.width = Math.max(0, g.w) + "px"; el.style.height = Math.max(0, g.h) + "px";
      el.style.borderRadius = g.r + "px";
      el.style.clipPath = g.wl > 0 || g.wr > 0 ? `inset(0 ${g.wr}% 0 ${g.wl}%)` : "none";
      const S = Math.max(g.w / 1280, g.h / 720) * c.z;
      let cx = c.cx, cy = c.cy;
      const hp = hero[P];
      if (hp && c.f > 0) { cx += (hp[0] - cx) * c.f; cy += (hp[1] - cy) * c.f; }
      const tx = clamp(g.w / 2 - cx * S, g.w - 1280 * S, 0), ty = clamp(g.h / 2 - cy * S, g.h - 720 * S, 0);
      camEl[P].style.transform = `translate(${tx}px,${ty}px) scale(${S})`;
    }
    function drawAll() {
      const t = tl.time();
      const done = new Set();
      for (let i = reel.length - 1; i >= 0; i--) {
        const r = reel[i];
        if (done.has(r.P) || t < r.t0 || t >= r.t1) continue;
        done.add(r.P);
        if (isRender()) drawFrame(r.P, r.clip, r.f0 + ((r.f1 - r.f0) * (t - r.t0)) / (r.t1 - r.t0), i);
        else liveFrame(r.P, r, t);
      }
      if (!isRender()) {
        for (const P of ["L", "R"]) if (!done.has(P)) wantK[P] = null;
        if (!PREVIEW) {
          prefetch(t);
          // 給 tools/playcheck.mjs: 主播放器有幾次該畫的格還沒解好 (畫面暫時停在上一張)
          const st = (root.VID_STATS = root.VID_STATS || { draws: 0, stale: [] });
          st.draws++;
          for (const P of ["L", "R"]) if (wantK[P] && shown[P] !== wantK[P]) st.stale.push(+t.toFixed(2));
        }
      }
      applyPan("L"); applyPan("R");
      drawFin();
    }

    // ---- 初始狀態 ----
    const hideAll = ["#divider", "#pls", "#band", "#rays", "#redv", "#redt", "#fx14", "#frame12", "#fin", "#th", "#pan10", "#black", "#flash",
      "#plus", "#c7", "#c7x", "#c11", "#q11", "#burst11", "#band11", "#c12", "#c14", "#bdL", "#bdR", "#shL", "#shR", "#hfL", "#hfR"].map($).filter(Boolean)
      .concat($$(".c4"), $$(".k5"), $$("#c5line"));
    for (const el of hideAll) { el.style.opacity = "0"; el.style.visibility = "hidden"; }
    tl.set(hideAll, { autoAlpha: 0 }, 0);
    tl.set([$("#pL"), $("#pR")], { autoAlpha: 1, x: 0, y: 0, rotation: 0, rotationX: 0, rotationY: 0, scale: 1, zIndex: 0, filter: "blur(9px) saturate(0.7)" }, 0);
    tl.set($("#fog"), { autoAlpha: 1 }, 0);
    tl.set($("#shake"), { x: 0, y: 0 }, 0);
    tl.set($("#world"), { x: 0, y: 0, scale: 1, skewX: 0, filter: "none" }, 0);
    tl.set([$("#tagL"), $("#tagR")], { xPercent: -50, yPercent: -50, autoAlpha: 0, rotation: 0, rotationX: 0, transformPerspective: 900 }, 0);
    tl.set($("#plus"), { xPercent: -50, yPercent: -50, x: 640, y: 340 }, 0);
    tl.set($("#divider"), { scaleY: 0 }, 0);
    tl.set($("#pls"), { x: PLUS[0], y: PLUS[1], scale: 1, rotation: 0 }, 0);
    tl.set($("#plsH"), { scaleX: 1 }, 0);
    tl.set($("#plsV"), { top: -48, height: 96, width: 26, left: -13 }, 0);
    tl.set($("#band"), { x: -400, skewX: -14 }, 0);
    tl.set(G.L, { x: 0, y: 0, w: 640, h: 720, r: 0, wl: 0, wr: 0 }, 0);
    tl.set(G.R, { x: 640, y: 0, w: 640, h: 720, r: 0, wl: 0, wr: 0 }, 0);

    const shake = (t, amp = 10, n = 6, el = $("#shake")) => tl.to(el, {
      keyframes: Array.from({ length: n }, (_, i) => ({ x: (i % 2 ? -1 : 1) * amp * (1 - i / n), y: ((i % 3) - 1) * amp * 0.5 * (1 - i / n), duration: 0.035 })).concat([{ x: 0, y: 0, duration: 0.035 }]),
    }, t);
    const flash = (t, a = 0.85, d = 0.18) => { tl.set($("#flash"), { autoAlpha: a }, t); tl.to($("#flash"), { autoAlpha: 0, duration: d }, t + 0.001); };
    const hide = (els, t) => tl.set(els, { autoAlpha: 0 }, t);

    // 片段與畫面位置 (片段內秒數, 見 STATUS.md「片段」)
    const DUN = { cx: 640, cy: 420, z: 1, f: 1 }, SHOW = { cx: 640, cy: 380, z: 1, f: 0 };
    const TAGPOS = { L: [356, 330], R: [962, 330] }, TAGTOP = { L: [320, 104], R: [960, 104] };

    // ===== K1 · 雙標籤開場 (背景: 霧化的左右實機畫面) =====
    {
      const s = starts.k1, k = pick("k1");
      shot("L", "dunA", 4.5, 4.5 + durs.k1 + durs.k2 + durs.k3, s, starts.k4, { ...DUN });
      shot("R", "showA", 2.0, 2.0 + durs.k1 + durs.k2 + durs.k3, s, starts.k4, { ...SHOW });
      const tL = $("#tagL"), tR = $("#tagR");
      if (k === "b") {
        // 由遠而近推進, 兩個標籤一前一後翻轉立起
        tl.set($("#world"), { scale: 1.12 }, s + 0.001);
        tl.to($("#world"), { scale: 1, duration: durs.k1 + durs.k2, ease: "power1.out" }, s + 0.002);
        fromTo(tL, { autoAlpha: 1, x: TAGPOS.L[0], y: TAGPOS.L[1], rotationX: -90, scale: 1 }, { rotationX: 0, duration: 0.45, ease: "back.out(2)" }, s + 0.15);
        fromTo(tR, { autoAlpha: 1, x: TAGPOS.R[0], y: TAGPOS.R[1], rotationX: -90, scale: 1 }, { rotationX: 0, duration: 0.45, ease: "back.out(2)" }, s + 0.55);
        cue("flip", s + 0.2, { id: "k1flip1" }); cue("flip", s + 0.6, { id: "k1flip2" });
        // 「+」轉一圈彈出來
        fromTo($("#pls"), { autoAlpha: 1, scale: 0, rotation: -180 }, { scale: 1, rotation: 0, duration: 0.35, ease: "back.out(2.5)" }, s + 1.0);
        cue("pop", s + 1.0, { id: "k1plus" });
      } else if (k === "c") {
        // 從左右兩側衝進中間, 相撞時白閃 + 震動
        fromTo(tL, { autoAlpha: 1, x: -300, y: TAGPOS.L[1], rotation: -8, scale: 1 }, { x: TAGPOS.L[0], rotation: 0, duration: 0.42, ease: "power3.in" }, s + 0.2);
        fromTo(tR, { autoAlpha: 1, x: 1600, y: TAGPOS.R[1], rotation: 8, scale: 1 }, { x: TAGPOS.R[0], rotation: 0, duration: 0.42, ease: "power3.in" }, s + 0.2);
        flash(s + 0.62, 0.7); shake(s + 0.62, 16, 8);
        cue("clash", s + 0.62);
        // 相撞的地方迸出「+」
        fromTo($("#pls"), { autoAlpha: 1, scale: 0, rotation: 90 }, { scale: 1, rotation: 0, duration: 0.3, ease: "back.out(3)" }, s + 0.64);
      } else {
        // 一個一個從上方砸下來
        fromTo(tL, { autoAlpha: 1, x: TAGPOS.L[0], y: TAGPOS.L[1], scale: 2.4, rotation: -6 }, { scale: 1, rotation: -3, duration: 0.3, ease: "power4.in" }, s + 0.2);
        fromTo(tR, { autoAlpha: 1, x: TAGPOS.R[0], y: TAGPOS.R[1], scale: 2.4, rotation: 6 }, { scale: 1, rotation: 3, duration: 0.3, ease: "power4.in" }, s + 0.75);
        shake(s + 0.5, 12); shake(s + 1.05, 12);
        cue("stamp", s + 0.5, { id: "k1stamp1" }); cue("stamp", s + 1.05, { id: "k1stamp2" });
        // 「+」也砸下來
        fromTo($("#pls"), { autoAlpha: 1, scale: 2.6, rotation: 20 }, { scale: 1, rotation: 0, duration: 0.22, ease: "power4.in" }, s + 1.25);
        shake(s + 1.47, 8, 4);
        cue("stamp", s + 1.47, { id: "k1stamp3" });
      }
    }

    // ===== K2 · 左右拆開, 霧化淡出 =====
    {
      const s = starts.k2, k = pick("k2");
      const tL = $("#tagL"), tR = $("#tagR");
      tl.to($("#fog"), { autoAlpha: 0, duration: 0.5 }, s + 0.1);
      tl.to(tL, { x: TAGTOP.L[0], y: TAGTOP.L[1], scale: 0.62, rotation: 0, rotationX: 0, duration: 0.55, ease: "power3.inOut" }, s + 0.05);
      tl.to(tR, { x: TAGTOP.R[0], y: TAGTOP.R[1], scale: 0.62, rotation: 0, rotationX: 0, duration: 0.55, ease: "power3.inOut" }, s + 0.05);
      // 「+」移到正中間, 橫槓收掉、直槓拉長變細, 變成中間的分隔線
      const tD = s + 0.45;
      tl.to($("#pls"), { x: 640, y: 360, scale: 1, rotation: 0, duration: 0.2, ease: "power2.inOut" }, s + 0.02);
      tl.to($("#plsH"), { scaleX: 0, duration: 0.18, ease: "power2.in" }, s + 0.1);
      tl.to($("#plsV"), { top: -380, height: 760, width: 8, left: -4, duration: 0.25, ease: "power3.out" }, s + 0.2);
      tl.set($("#divider"), { autoAlpha: 1, scaleY: 1 }, tD);
      hide($("#pls"), tD);
      cue("slash", s + 0.2, { id: "k2plus" });
      if (k === "b") {
        // 左邊從上滑下、右邊從下滑上, 交錯就位
        tl.to([$("#pL"), $("#pR")], { filter: "blur(0px) saturate(1)", duration: 0.5 }, s + 0.1);
        fromTo(G.L, { y: -720 }, { y: 0, duration: 0.55, ease: "power3.out" }, s + 0.05);
        fromTo(G.R, { y: 720 }, { y: 0, duration: 0.55, ease: "power3.out" }, s + 0.05);
        flash(s + 0.6, 0.35, 0.12);
        cue("whoosh", s + 0.05, { id: "k2whoosh" });
      } else if (k === "c") {
        // 兩片像卡片一樣翻面, 翻過來就是清楚的畫面
        [["#pL", 0.05], ["#pR", 0.2]].forEach(([id, d]) => {
          tl.to($(id), { keyframes: [{ rotationY: 90, duration: 0.18, ease: "power2.in" }, { rotationY: 0, duration: 0.2, ease: "power2.out" }] }, s + d);
          tl.set($(id), { filter: "blur(0px) saturate(1)" }, s + d + 0.18);
        });
        cue("flip", s + 0.15, { id: "k2flip1" }); cue("flip", s + 0.3, { id: "k2flip2" });
      } else {
        // 中線一刀切開: 「+」拉成分隔線, 兩半往外退開一點
        tl.to([$("#pL"), $("#pR")], { filter: "blur(0px) saturate(1)", duration: 0.5 }, s + 0.1);
        tl.to(G.L, { x: -24, duration: 0.25, ease: "power2.out", yoyo: true, repeat: 1 }, s + 0.3);
        tl.to(G.R, { x: 664, duration: 0.25, ease: "power2.out", yoyo: true, repeat: 1 }, s + 0.3);
      }
    }

    // ===== K3 · 聚焦「搜打撤」: 左畫面變全畫面, 右邊連同「自動經營」移出 =====
    {
      const s = starts.k3, k = pick("k3");
      const tL = $("#tagL"), tR = $("#tagR");
      tl.to($("#divider"), { autoAlpha: 0, duration: 0.15 }, s);
      if (k === "b") {
        // 右邊先變暗、轉著飛出去, 左邊再展開; 「搜打撤」放大到中間後淡掉
        tl.to($("#shR"), { autoAlpha: 0.7, duration: 0.2 }, s);
        tl.to(G.R, { x: 1500, duration: 0.45, ease: "power3.in" }, s + 0.1);
        tl.to($("#pR"), { rotation: 14, duration: 0.45, ease: "power3.in" }, s + 0.1);
        tl.to(tR, { x: 1700, rotation: 20, duration: 0.45, ease: "power3.in" }, s + 0.1);
        tl.to(G.L, { w: 1280, duration: 0.45, ease: "power3.out" }, s + 0.45);
        tl.to(C.L, { z: 1.6, duration: 0.6, ease: "power2.out" }, s + 0.4);
        tl.to(tL, { x: 640, y: 330, scale: 1.25, duration: 0.4, ease: "back.out(1.6)" }, s + 0.25);
        tl.to(tL, { autoAlpha: 0, scale: 1.6, duration: 0.25 }, s + 0.8);
        cue("whoosh", s + 0.1, { id: "k3whoosh" }); cue("pop", s + 0.3, { id: "k3pop" });
      } else if (k === "c") {
        // 金色斜帶從左掃到右, 帶走右半邊與「自動經營」; 「搜打撤」縮成左上角的章節標籤
        tl.set(G.L, { w: 1280 }, s + 0.001);
        tl.set($("#pR"), { zIndex: 1 }, s + 0.001);
        tl.set($("#band"), { autoAlpha: 1 }, s + 0.002);
        fromTo($("#band"), { x: 300 }, { x: 1500, duration: 0.55, ease: "power2.inOut" }, s + 0.003);
        fromTo(G.R, { wl: 0 }, { wl: 100, duration: 0.55, ease: "power2.inOut" }, s + 0.003);
        tl.to(tR, { x: 1700, duration: 0.45, ease: "power2.in" }, s + 0.1);
        tl.to(C.L, { z: 1.6, duration: 0.7, ease: "power2.inOut" }, s + 0.1);
        tl.to(tL, { x: 150, y: 64, scale: 0.34, duration: 0.5, ease: "power3.inOut" }, s + 0.3);
        hide($("#band"), s + 0.6);
        cue("swipe", s + 0.05);
      } else {
        // 左邊直接把右邊推出去; 「搜打撤」先放大跳一下再縮到左上角
        tl.to(G.L, { w: 1280, duration: 0.55, ease: "power3.inOut" }, s + 0.05);
        tl.to(G.R, { x: 1280, duration: 0.55, ease: "power3.inOut" }, s + 0.05);
        tl.to(tR, { x: 1280 + 320, duration: 0.55, ease: "power3.inOut" }, s + 0.05);
        tl.to(C.L, { z: 1.6, duration: 0.7, ease: "power2.inOut" }, s + 0.1);
        tl.to(tL, { x: 640, y: 300, scale: 1.05, duration: 0.3, ease: "back.out(2)" }, s + 0.05);
        tl.to(tL, { x: 150, y: 64, scale: 0.34, duration: 0.35, ease: "power3.in" }, s + 0.55);
        cue("push", s + 0.05);
      }
    }

    // ===== K4 · 玩法快閃: 探索 / 開寶箱 / 打怪 (每個畫面只顯示自己的字) =====
    {
      const s = starts.k4, k = pick("k4"), d = durs.k4 / 3;
      // 探索 = 草地走路, 開寶箱 = 開箱跳出鑰匙卡, 打怪 = 揮兩下打倒 (片段內起秒, 各鋪 d 秒)
      const SH = [["chest2", 2.2], ["dunA", 12.6, { cx: 640, cy: 400, z: 1.15, f: 0 }], ["kill", 1.1]];
      const caps = $$(".c4");
      if (k === "c") {
        // 畫面縮成一張卡片, 每換一個就從右邊滑進來, 字是卡片左上角的貼紙
        tl.to(G.L, { x: 70, y: 40, w: 1140, h: 641, r: 22, duration: 0.2, ease: "power2.out" }, s);
        tl.set($("#bdL"), { autoAlpha: 1 }, s);
      }
      SH.forEach(([clip, a, cam], i) => {
        const t0 = s + i * d, t1 = t0 + d;
        shot("L", clip, a, a + d, t0 + 0.0001, t1, cam || { ...DUN, z: 2.1 });
        const c = caps[i];
        if (k === "b") {
          // 每切一刀白閃 + 甩鏡, 大字斜放在畫面下方 (不擋中間的主角)
          if (i) flash(t0, 0.9, 0.12);
          fromTo($("#pL"), { x: i % 2 ? -90 : 90 }, { x: 0, duration: 0.14, ease: "power2.out" }, t0 + 0.0002);
          fromTo(c, { autoAlpha: 1, scale: 1.8, rotation: i % 2 ? 4 : -4 }, { scale: 1, duration: 0.18, ease: "back.out(2.2)" }, t0 + 0.0003);
        } else if (k === "c") {
          if (i) fromTo($("#pL"), { x: 1300 }, { x: 0, duration: 0.16, ease: "power3.out" }, t0 + 0.0002);
          fromTo(c, { autoAlpha: 1, scale: 0, rotation: -8 }, { scale: 1, rotation: -4, duration: 0.2, ease: "back.out(2.5)" }, t0 + 0.08);
        } else {
          // 硬切, 字從下方彈上來, 畫面微微推近
          fromTo(c, { autoAlpha: 1, y: 40, scale: 0.85 }, { y: 0, scale: 1, duration: 0.18, ease: "back.out(2.5)" }, t0 + 0.0003);
          fromTo(C.L, { z: cam ? cam.z : 2.0 }, { z: (cam ? cam.z : 2.0) + 0.25, duration: d, ease: "none" }, t0 + 0.0004);
        }
        hide(c, t1 - 0.0001);
        cue("cut", t0, { id: "k4cut" + i });
      });
      cue("hit", s + 2 * d + 0.4, { id: "k4kill" });
    }

    // ===== K5 · 抓怪疊字: 抓怪、抓怪、抓更多的怪 =====
    // [片段, 片段內起秒]: 中間是套索收緊、「收服!」
    const CAPSH = [["cap1", 0.85], ["cap8", 0.55], ["cap3", 0.85], ["cap4", 0.85]];
    {
      const s = starts.k5, k = pick("k5"), d = durs.k5 / 3;
      tl.set(G.L, { x: 0, y: 0, w: 1280, h: 720, r: 0 }, s);
      tl.set($("#pL"), { x: 0 }, s + 0.0005);
      tl.set($("#bdL"), { autoAlpha: 0 }, s + 0.0005);
      if (k === "a") tl.set($("#c5line"), { autoAlpha: 1 }, s);
      for (let i = 0; i < 3; i++) {
        const t0 = s + i * d, [clip, a] = CAPSH[i];
        shot("L", clip, a, a + d, t0 + 0.0001, t0 + d, { ...DUN, z: 2.2 });
        const el = $("#c5_" + i);
        if (k === "b") fromTo(el, { autoAlpha: 1, scale: 0, transformOrigin: "0% 100%" }, { scale: 1, duration: 0.2, ease: "back.out(2.4)" }, t0 + 0.0003);
        else if (k === "c") { fromTo(el, { autoAlpha: 1, scale: 2, rotation: i === 2 ? -6 : (i ? 7 : -9) }, { scale: 1, duration: 0.16, ease: "power4.in" }, t0 + 0.0003); shake(t0 + 0.17, 6, 4); }
        else fromTo(el, { autoAlpha: 1, scale: 1.6, y: -10 }, { scale: 1, y: 0, duration: 0.18, ease: "back.out(2.5)" }, t0 + 0.0003);
        cue("cut", t0, { id: "k5cut" + i }); cue("pop", t0 + 0.05, { id: "k5pop" + i });
      }
    }

    // ===== K6 · 「抓更多的怪」固定住並強調, 再閃一個抓怪畫面 =====
    {
      const s = starts.k6, k = pick("k6"), d = durs.k6;
      const more = $("#c5_2");
      const [clip, a] = CAPSH[3];
      shot("L", clip, a, a + d, s + 0.0001, s + d, { ...DUN, z: 2.2 });
      cue("cut", s, { id: "k6cut0" });
      if (k === "b") {
        // 切畫面時震一下、字再放大一點, 背後集中線
        fromTo(more, { scale: 1.37 }, { scale: 1.12, duration: 0.14, ease: "power3.out" }, s + 0.0003);
        shake(s + 0.0004, 9, 5);
        tl.set($("#rays"), { autoAlpha: 1 }, s);
        fromTo($("#rays"), { rotation: 0 }, { rotation: 6, duration: d, ease: "none" }, s + 0.0001);
        hide($("#rays"), s + d);
      } else if (k === "c") {
        fromTo(more, { scale: 1.12 }, { scale: 1, duration: 0.25, ease: "power2.out" }, s + 0.0003);
        // 字的外框一圈一圈往外擴散 (殘影): 複製 3 份放在同一個位置
        for (let j = 0; j < 3; j++) {
          const ghost = more.cloneNode(true);
          ghost.removeAttribute("id"); ghost.classList.remove("k5", "more");
          Object.assign(ghost.style, { position: "absolute", left: more.offsetLeft + "px", top: more.offsetTop + "px", right: "auto", bottom: "auto", margin: "0",
            color: "transparent", webkitTextStroke: "4px " + GOLD, textShadow: "none", background: "transparent", borderColor: "transparent", boxShadow: "none", opacity: "0", visibility: "hidden" });
          more.parentNode.insertBefore(ghost, more);
          tl.set(ghost, { autoAlpha: 0 }, 0);
          for (let i = 0; i * 0.3 + j * 0.1 + 0.5 <= d; i++) fromTo(ghost, { autoAlpha: 0.9, scale: 1 }, { autoAlpha: 0, scale: 1.7, duration: 0.5, ease: "power1.out" }, s + i * 0.3 + j * 0.1);
        }
      } else {
        fromTo(more, { scale: 1.3 }, { scale: 1, duration: 0.2, ease: "back.out(3)" }, s + 0.0003);
        tl.set(more, { color: "#ff5b6e" }, s + 0.0004);
      }
      if (k === "a") tl.set(more, { color: pick("k5") === "c" ? "#fff" : GOLD }, 0.0009);
      hide($$(".k5").concat($$("#c5line")), s + d);
    }

    // ===== K7 · 奴役 → 帶領他們去表演 (怪物排隊走進帳篷) =====
    {
      const s = starts.k7, k = pick("k7");
      // im 片段: 4.4 秒起排隊走向帳篷, 最後一隻約 8.1 秒進門; K7 鋪 4.4~7.4, K7b 接著 7.4~8.15
      const IM = [4.4, 7.4];
      shot("L", "im", IM[0], IM[1], s, starts.k7b, { cx: 560, cy: 380, z: 1.35, f: 0 });
      // 遊戲下方會閃「按 Z 繼續」: 畫片段時用旁邊的地板蓋掉 (見 PATCH)
      tl.set($("#c7"), { autoAlpha: 1 }, s + 0.0002);
      const w = $("#c7w"), o = $("#c7o"), st = $("#c7s"), n = $("#c7n"), r = $("#c7r");
      tl.set(st, { scaleX: 0 }, 0.0005);
      tl.set(n, { autoAlpha: 0 }, 0.0006);
      tl.set(r, { autoAlpha: 0 }, 0.0007);
      if (k === "c") {
        // 改稿: 「奴役」被紅筆劃掉變灰, 上方手寫「帶領 ✓」
        tl.set(n, { xPercent: -50, rotation: -6 }, 0.0008);
        tl.set(w, { color: "#fff" }, 0.0009);
        fromTo(w, { autoAlpha: 1, scale: 1.3 }, { scale: 1, duration: 0.2, ease: "back.out(2)" }, s + 0.05);
        tl.to(w, { x: -8, duration: 0.05, yoyo: true, repeat: 5 }, s + 0.55);
        fromTo(st, { scaleX: 0 }, { scaleX: 1, duration: 0.18, ease: "power2.in" }, s + 0.95);
        tl.to(w, { color: "#9a9a9a", duration: 0.15 }, s + 1.13);
        fromTo(n, { autoAlpha: 1, scale: 0 }, { scale: 1, duration: 0.25, ease: "back.out(2.5)" }, s + 1.3);
        fromTo(r, { autoAlpha: 1, x: 30 }, { x: 0, duration: 0.25, ease: "power2.out" }, s + 1.6);
        cue("pop", s + 0.05, { id: "k7pop" }); cue("scratch", s + 0.55); cue("strike", s + 0.95); cue("write", s + 1.3);
      } else {
        const x = $("#c7x");
        tl.set(o, { autoAlpha: 1, x: 0, y: 0, rotation: 0, scale: 1 }, 0.0008);
        fromTo(w, { autoAlpha: 1, scale: 1.4 }, { scale: 1, duration: 0.2, ease: "back.out(2)" }, s + 0.05);
        if (k === "b") {
          // 畫面停格去色, 跳出「欸?不對!」, 劃線後「奴役」被揉成一團丟掉, 畫面恢復
          tl.to($("#world"), { filter: "grayscale(1) brightness(0.6)", duration: 0.1 }, s + 0.5);
          seg("L", "im", IM[0] + 0.5, IM[0] + 0.5, s + 0.5, s + 1.45);
          seg("L", "im", IM[0] + 0.5, IM[1], s + 1.45, starts.k7b);
          fromTo(x, { autoAlpha: 1, scale: 0, rotation: -10 }, { scale: 1, rotation: 4, duration: 0.2, ease: "back.out(3)" }, s + 0.55);
          fromTo(st, { scaleX: 0 }, { scaleX: 1, duration: 0.15 }, s + 0.9);
          tl.to(o, { scale: 0.2, rotation: 540, x: -260, y: -300, autoAlpha: 0, duration: 0.4, ease: "power2.in" }, s + 1.1);
          tl.to(x, { autoAlpha: 0, duration: 0.15 }, s + 1.1);
          tl.to($("#world"), { filter: "grayscale(0) brightness(1)", duration: 0.15 }, s + 1.45);
          tl.set($("#world"), { filter: "none" }, s + 1.61);
        } else {
          // 「奴役」出現後一頓, 冒出「欸?不對!」, 紅線劃過, 字被扯掉往下掉
          tl.to(w, { rotation: -4, duration: 0.06, yoyo: true, repeat: 3 }, s + 0.5);
          fromTo(x, { autoAlpha: 1, y: 30, scale: 0.6 }, { y: 0, scale: 1, duration: 0.18, ease: "back.out(3)" }, s + 0.55);
          fromTo(st, { scaleX: 0 }, { scaleX: 1, duration: 0.15 }, s + 0.95);
          tl.to(o, { y: 260, rotation: 35, autoAlpha: 0, duration: 0.45, ease: "power2.in" }, s + 1.15);
          tl.to(x, { autoAlpha: 0, duration: 0.15 }, s + 1.15);
        }
        fromTo(n, { autoAlpha: 1, y: -120, scale: 1.6 }, { y: 0, scale: 1, duration: 0.22, ease: "power4.in" }, s + 1.5);
        shake(s + 1.72, 8, 5);
        fromTo(r, { autoAlpha: 1, x: 30 }, { x: 0, duration: 0.25, ease: "power2.out" }, s + 1.75);
        cue("pop", s + 0.05, { id: "k7pop" }); cue("scratch", s + 0.5); cue("strike", s + 0.95); cue("stamp", s + 1.72, { id: "k7stamp" });
      }
    }

    // ===== K7b · 進帳篷: 最後一隻怪物進門時鏡頭衝進帳篷入口, 黑畫面撐滿、停一下, 接猴子小劇場 =====
    {
      const s = starts.k7b, d = durs.k7b;
      // 8.15 秒最後一隻剛消失在門裡; 8.2 秒起門會亮起來, 所以停在 8.15
      seg("L", "im", 7.4, 8.15, s, s + 0.9);
      seg("L", "im", 8.15, 8.15, s + 0.9, starts.k10);
      tl.to($("#c7"), { autoAlpha: 0, duration: 0.25 }, s + 0.1);
      tl.to([$("#tagL"), $("#tagR")], { autoAlpha: 0, duration: 0.2 }, s);
      // 帳篷入口在片段座標約 (640, 520); 先慢後快推進去, 門裡的暗色撐滿畫面
      tl.to(C.L, { cx: 640, cy: 535, duration: 0.5, ease: "power2.out" }, s + 0.05);
      tl.to(C.L, { z: 14, duration: 0.95, ease: "power3.in" }, s + 0.05);
      tl.set($("#black"), { autoAlpha: 0 }, s);
      tl.to($("#black"), { autoAlpha: 1, duration: 0.15 }, s + 0.85);
      cue("enter", s + 0.7, { id: "k7benter" });
    }


    // ===== K10 · 猴子小劇場 (非遊戲畫面): 暗 → 聚光燈 → 對看 → 驚訝 → 生氣丟火柴 → 互丟 → 觀眾鼓掌 =====
    {
      const s = starts.k10, k = pick("k10"), th = $("#th");
      const q = (c) => th.querySelector(c), qa = (c) => [...th.querySelectorAll(c)];
      const m1 = q(".m1"), m2 = q(".m2");
      const part = (m, c) => m.querySelector(c);
      // 起始姿勢 (0 秒就設好, 循環回來才一樣)
      const off = [q(".sp1"), q(".sp2"), q(".sp3"), q(".ex1"), q(".ex2"), q(".an1"), q(".an2"), ...qa(".mt"), ...qa(".bm")];
      for (const m of [m1, m2]) off.push(...[".eyS", ".eyA", ".mS", ".mA", ".fl"].map((c) => part(m, c)));
      tl.set(off, { opacity: 0 }, 0);
      tl.set([m1, m2], { opacity: 0, y: 0, x: 0 }, 0);
      tl.set([m1, m2].flatMap((m) => [part(m, ".eyN"), part(m, ".mN")]), { opacity: 1 }, 0);
      tl.set([part(m1, ".hd"), part(m2, ".hd")], { rotation: 0, svgOrigin: "0 -100" }, 0);
      tl.set([part(m1, ".arm"), part(m2, ".arm")], { rotation: 0, svgOrigin: "20 -90" }, 0);
      tl.set(qa(".pu"), { x: 0 }, 0);
      tl.set([...qa(".mt"), ...qa(".bm")], { x: 0, y: 0, rotation: 0, scale: 1, transformOrigin: "50% 50%" }, 0.0001);
      tl.set([q(".ex1"), q(".ex2"), q(".an1"), q(".an2")], { scale: 1, transformOrigin: "50% 50%" }, 0.0001);
      tl.set(q(".crowd"), { y: 220 }, 0);
      tl.set(q(".tcam"), { scale: 1, x: 0, y: 0, svgOrigin: "640 360" }, 0);
      // 進場: 接著帳篷裡的黑畫面, 黑幕在第一盞聚光燈打下時退掉
      tl.set(th, { autoAlpha: 1 }, s);
      tl.to($("#black"), { autoAlpha: 0, duration: 0.3 }, s + 0.2);
      tl.set([$("#pL"), $("#pR"), $("#tagL"), $("#tagR")], { autoAlpha: 0 }, s + 0.0001);
      // 聚光燈依序打下 (每盞閃一下才亮)
      [[".sp1", 0.25, m1], [".sp2", 0.5, m2], [".sp3", 0.75, null]].forEach(([c, t, m], i) => {
        tl.to(q(c), { keyframes: [{ opacity: 1, duration: 0.04 }, { opacity: 0.3, duration: 0.04 }, { opacity: 1, duration: 0.05 }] }, s + t);
        if (m) tl.to(m, { opacity: 1, duration: 0.08 }, s + t + 0.04);
        cue("spot", s + t, { id: "k10spot" + i });
      });
      // 對看: 頭轉向對方、眼珠移過去
      tl.to(qa(".m1 .pu"), { x: 7, duration: 0.15 }, s + 1.0);
      tl.to(qa(".m2 .pu"), { x: 7, duration: 0.15 }, s + 1.05);
      tl.to([part(m1, ".hd"), part(m2, ".hd")], { rotation: 8, duration: 0.2 }, s + 1.0);
      // 驚訝: ! 跳出、跳一下、眼睛嘴巴變
      const face = (m, from, to, t) => { tl.set([part(m, ".ey" + from), part(m, ".m" + from)], { opacity: 0 }, t); tl.set([part(m, ".ey" + to), part(m, ".m" + to)], { opacity: 1 }, t + 0.0001); };
      face(m1, "N", "S", s + 1.4); face(m2, "N", "S", s + 1.4);
      fromTo([q(".ex1"), q(".ex2")], { opacity: 1, scale: 0 }, { scale: 1, duration: 0.15, ease: "back.out(3)" }, s + 1.4);
      tl.to([m1, m2], { y: -22, duration: 0.1, yoyo: true, repeat: 1, ease: "power2.out" }, s + 1.4);
      tl.to([q(".ex1"), q(".ex2")], { opacity: 0, duration: 0.1 }, s + 1.75);
      cue("surprise", s + 1.4);
      // 左邊那隻先生氣
      face(m1, "S", "A", s + 1.85);
      tl.to(part(m1, ".fl"), { opacity: 0.55, duration: 0.15 }, s + 1.85);
      fromTo(q(".an1"), { opacity: 1, scale: 0 }, { scale: 1, duration: 0.15, ease: "back.out(3)" }, s + 1.85);
      tl.to(m1, { x: -4, duration: 0.04, yoyo: true, repeat: 5 }, s + 1.9);
      cue("angry", s + 1.85, { id: "k10angry1" });
      // 丟火柴: 從手上拋到對方頭上
      const H1 = [500, 470], H2 = [780, 470], HEAD1 = [430, 400], HEAD2 = [850, 400];
      const throwM = (i, from, to, t, dur = 0.3) => {
        const mt = q(".mt" + i), bm = q(".bm" + i), dir = to[0] > from[0] ? 1 : -1, r0 = dir > 0 ? -30 : 210;
        tl.set(mt, { x: from[0], y: from[1], rotation: r0, opacity: 1 }, t);
        tl.to(mt, { x: to[0], rotation: r0 + dir * 540, duration: dur, ease: "none" }, t + 0.0001);
        tl.to(mt, { keyframes: [{ y: Math.min(from[1], to[1]) - 140, duration: dur / 2, ease: "power2.out" }, { y: to[1], duration: dur / 2, ease: "power2.in" }] }, t + 0.0001);
        tl.set(mt, { opacity: 0 }, t + dur);
        tl.set(bm, { x: to[0], y: to[1] }, 0.001 + i * 0.0001);
        fromTo(bm, { opacity: 1, scale: 0.2 }, { scale: 1.2, opacity: 0, duration: 0.25, ease: "power2.out" }, t + dur);
        cue("throw", t, { id: "k10throw" + i }); cue("hit", t + dur, { id: "k10hit" + i });
      };
      tl.to(part(m1, ".arm"), { rotation: -70, duration: 0.08, yoyo: true, repeat: 1 }, s + 2.15);
      throwM(0, H1, HEAD2, s + 2.2);
      tl.to(m2, { x: 10, duration: 0.05, yoyo: true, repeat: 3 }, s + 2.5);
      // 右邊那隻被丟到也生氣, 丟回去
      face(m2, "S", "A", s + 2.6);
      tl.to(part(m2, ".fl"), { opacity: 0.55, duration: 0.15 }, s + 2.6);
      fromTo(q(".an2"), { opacity: 1, scale: 0 }, { scale: 1, duration: 0.15, ease: "back.out(3)" }, s + 2.6);
      cue("angry", s + 2.6, { id: "k10angry2" });
      tl.to(part(m2, ".arm"), { rotation: -70, duration: 0.08, yoyo: true, repeat: 1 }, s + 2.8);
      throwM(1, H2, HEAD1, s + 2.85);
      // 互丟
      for (let i = 2; i < 10; i++) {
        const t = s + 3.2 + (i - 2) * 0.16, l2r = i % 2 === 0;
        throwM(i, l2r ? H1 : H2, l2r ? [HEAD2[0] + ((i * 17) % 30) - 15, HEAD2[1] - 10] : [HEAD1[0] + ((i * 23) % 30) - 15, HEAD1[1] - 10], t, 0.24);
      }
      tl.to([m1, m2], { y: -10, duration: 0.08, yoyo: true, repeat: 9 }, s + 3.2);
      // 觀眾從下面升起來鼓掌 (拍手的表現另有方案 k10clap)
      const pps = qa(".pp"), kc = pick("k10clap"), c0 = s + 3.3;
      pps.forEach((pp) => {
        for (const c of ["al", "ar"]) { const g = pp.querySelector("." + c); tl.set(g, { rotation: 0, svgOrigin: g.dataset.o }, 0); }
        tl.set(pp.querySelector(".pb"), { y: 0, x: 0 }, 0);
        tl.set([pp.querySelector(".ci"), pp.querySelector(".pa"), pp.querySelector(".ht")], { opacity: 0, scale: 1, x: 0, y: 0, transformOrigin: "50% 50%" }, 0);
      });
      tl.set(q(".cfs"), { opacity: 0 }, 0);
      tl.set(qa(".cf"), { y: 0, rotation: 0, transformOrigin: "50% 50%" }, 0);
      tl.to(q(".crowd"), { y: -90, duration: 0.35, ease: "power3.out" }, c0);
      // 一次拍手: 兩手往中間轉到碰在一起再張開; fx = 碰到那一刻要亮的裝飾
      const clap = (pp, t, dur, fx) => {
        const al = pp.querySelector(".al"), ar = pp.querySelector(".ar");
        tl.to(al, { rotation: 9, duration: dur * 0.4, ease: "power2.in" }, t);
        tl.to(ar, { rotation: -9, duration: dur * 0.4, ease: "power2.in" }, t);
        tl.to([al, ar], { rotation: 0, duration: dur * 0.6, ease: "power2.out" }, t + dur * 0.4);
        if (fx) { tl.set(fx, { opacity: 1, scale: 0.6 }, t + dur * 0.4); tl.to(fx, { scale: 1.2, opacity: 0, duration: dur * 0.6, ease: "power1.out" }, t + dur * 0.4 + 0.001); }
      };
      if (kc === "b") {
        // 起立歡呼: 雙手舉高左右揮, 一個接一個跳起來 (波浪), 上方灑紙花
        pps.forEach((pp, i) => {
          const al = pp.querySelector(".al"), ar = pp.querySelector(".ar"), t = c0 + 0.1 + i * 0.03;
          tl.to(al, { rotation: -22, duration: 0.15 }, t); tl.to(ar, { rotation: 22, duration: 0.15 }, t);
          tl.to(al, { rotation: -12, duration: 0.13, yoyo: true, repeat: 5, ease: "sine.inOut" }, t + 0.15);
          tl.to(ar, { rotation: 12, duration: 0.13, yoyo: true, repeat: 5, ease: "sine.inOut" }, t + 0.15);
          tl.to(pp.querySelector(".pb"), { y: -26, duration: 0.14, yoyo: true, repeat: 3, ease: "power2.out" }, c0 + 0.25 + i * 0.05);
        });
        tl.set(q(".cfs"), { opacity: 1 }, c0);
        tl.to(qa(".cf"), { y: (i) => 760 + (i % 5) * 30, rotation: (i) => (i % 2 ? 540 : -540), duration: 1.3, ease: "none", stagger: 0.008 }, c0);
        cue("cheer", c0 + 0.1);
      } else if (kc === "c") {
        // 啪! 啪!: 手確實拍在一起, 拍到的那一刻頭上冒「啪!」(輪流)
        pps.forEach((pp, i) => { for (let n = 0; n < 3; n++) clap(pp, c0 + 0.3 + n * 0.3 + (i % 2) * 0.15, 0.24, (i + n) % 3 === 0 ? pp.querySelector(".pa") : pp.querySelector(".ci")); });
        cue("clap", c0 + 0.3);
      } else if (kc === "d") {
        // 愛心: 邊拍手邊左右搖, 頭上一顆顆愛心往上飄
        pps.forEach((pp, i) => {
          for (let n = 0; n < 4; n++) clap(pp, c0 + 0.3 + n * 0.22 + (i % 3) * 0.05, 0.2, null);
          tl.to(pp.querySelector(".pb"), { x: i % 2 ? 6 : -6, duration: 0.25, yoyo: true, repeat: 3, ease: "sine.inOut" }, c0 + 0.3);
          const ht = pp.querySelector(".ht"), t = c0 + 0.35 + ((i * 5) % 7) * 0.08;
          tl.set(ht, { opacity: 1, scale: 0.4 }, t);
          tl.to(ht, { y: -150, scale: 1.3, duration: 0.7, ease: "power1.out" }, t + 0.001);
          tl.to(ht, { opacity: 0, duration: 0.2 }, t + 0.5);
        });
        cue("clap", c0 + 0.3);
      } else {
        // 拍手: 每個人各自的節奏, 兩手碰到時冒一圈白色衝擊線
        pps.forEach((pp, i) => { for (let n = 0; n < 4; n++) clap(pp, c0 + 0.25 + n * 0.22 + ((i * 7) % 4) * 0.04, 0.18, pp.querySelector(".ci")); });
        cue("clap", c0 + 0.25);
      }
      if (k === "b") {
        // 漫畫分格: 對看到第一次丟中這段切成左右兩格特寫
        tl.set($("#pan10"), { autoAlpha: 1 }, s + 0.98);
        tl.set($("#pan10"), { autoAlpha: 0 }, s + 3.0);
        flash(s + 0.98, 0.6, 0.1); flash(s + 3.0, 0.6, 0.1);
        cue("panel", s + 0.98);
      } else if (k === "c") {
        // 鏡頭跟著劇情移動: 跟聚光燈 → 推到生氣的臉 → 跟著火柴甩過去 → 拉遠露出觀眾
        tl.set(q(".tcam"), { scale: 1.7, x: 374, y: -150 }, s + 0.001);
        tl.to(q(".tcam"), { x: -374, duration: 0.25, ease: "power2.inOut" }, s + 0.45);
        tl.to(q(".tcam"), { scale: 1, x: 0, y: 0, duration: 0.35, ease: "power2.inOut" }, s + 0.75);
        tl.to(q(".tcam"), { scale: 2.1, x: 462, y: -84, duration: 0.25, ease: "power3.out" }, s + 1.8);
        tl.to(q(".tcam"), { x: -462, duration: 0.3, ease: "power2.inOut" }, s + 2.2);
        tl.to(q(".tcam"), { x: 462, duration: 0.3, ease: "power2.inOut" }, s + 2.85);
        tl.to(q(".tcam"), { scale: 0.92, x: 0, y: -40, duration: 0.45, ease: "power2.inOut" }, s + 3.2);
      } else {
        // 全景一鏡到底, 最後微微推近
        tl.to(q(".tcam"), { scale: 1.06, duration: durs.k10 - 1, ease: "none" }, s + 1);
      }
      hide(th, s + durs.k10);
    }

    // ===== K12 · 安排表演節目 (表演前設定頁; 猴子小劇場後第一個) =====
    {
      const s = starts.k12, k = pick("k12"), e = s + durs.k12;
      tl.set(G.R, { x: 0, y: 0, w: 1280, h: 720, r: 0, wl: 0, wr: 0 }, s);
      tl.set($("#pR"), { autoAlpha: 1, rotation: 0, x: 0, zIndex: 1, filter: "none" }, s + 0.0001);
      tl.set($("#shR"), { autoAlpha: 0 }, s + 0.0001);
      shot("R", "setup", 11.5, 11.5 + durs.k12, s, e, { cx: 640, cy: 360, z: 1, f: 0 });
      const c = $("#c12");
      if (k === "a") {
        // 設定頁像一台平板斜放, 慢慢轉正
        tl.set(G.R, { x: 110, y: 40, w: 1060, h: 596, r: 18 }, s + 0.0002);
        tl.set($("#bdR"), { autoAlpha: 1 }, s);
        fromTo($("#pR"), { rotationX: 24, rotationY: -22, scale: 0.9 }, { rotationX: 6, rotationY: -6, scale: 1, duration: durs.k12, ease: "power2.out" }, s + 0.0003);
        fromTo(c, { autoAlpha: 1, y: 40 }, { y: 0, duration: 0.25, ease: "back.out(2)" }, s + 0.15);
        tl.set($("#pR"), { rotationX: 0, rotationY: 0, scale: 1 }, e);
        tl.set($("#bdR"), { autoAlpha: 0 }, e);
        tl.set(G.R, { x: 0, y: 0, w: 1280, h: 720, r: 0 }, e + 0.0001);
      } else if (k === "b") {
        // 鏡頭推近到正在選的那一列
        fromTo(C.R, { cx: 640, cy: 360, z: 1 }, { cx: 600, cy: 230, z: 1.8, duration: 0.8, ease: "power3.inOut" }, s + 0.0002);
        fromTo(c, { autoAlpha: 1, scale: 0.6 }, { scale: 1, duration: 0.2, ease: "back.out(2.5)" }, s + 0.15);
      } else {
        // 全畫面 + 金框標出節目表
        tl.set($("#frame12"), { autoAlpha: 1 }, s + 0.2);
        fromTo($("#frame12"), { scale: 1.3 }, { scale: 1, duration: 0.25, ease: "back.out(2)" }, s + 0.2);
        tl.to($("#frame12"), { opacity: 0.5, duration: 0.25, yoyo: true, repeat: 3 }, s + 0.6);
        fromTo(c, { autoAlpha: 1, x: -80 }, { x: 0, duration: 0.25, ease: "power3.out" }, s + 0.1);
        hide($("#frame12"), e);
      }
      hide(c, e);
      cue("cut", s, { id: "k12cut" }); cue("pop", s + 0.15, { id: "k12pop" });
    }

    // ===== K11 · 大亂鬥: 讓怪物們大亂鬥! 打得越激烈觀眾越愛看; 最後觀眾冒出「我要看到血流成河!」 =====
    {
      const s = starts.k11, k = pick("k11"), e = s + durs.k11, d = 0.55;
      // 前 4 個快閃 (各 0.55 秒), 最後一個鏡頭停久一點給對話框 (show5 上排黃衣觀眾在 (842, 88))
      const SH = [["show5", 4.0], ["showA", 18.5], ["show5", 2.6], ["showA", 2.0]];
      const tq = s + 4 * d;
      SH.forEach(([clip, x0], i) => {
        const t0 = s + i * d;
        shot("R", clip, x0, x0 + d, t0 + 0.0001, t0 + d, { cx: 640, cy: 380, z: 1.0, f: 0 });
        if (i) { flash(t0, 0.5, 0.1); fromTo($("#pR"), { rotation: i % 2 ? 2 : -2 }, { rotation: 0, duration: 0.2 }, t0 + 0.0002); }
        cue("cut", t0, { id: "k11cut" + i });
      });
      shot("R", "show5", 6.0, 6.0 + (e - tq), tq + 0.0001, e, { cx: 640, cy: 380, z: 1.0, f: 0 });
      flash(tq, 0.5, 0.1); cue("cut", tq, { id: "k11cut4" });
      tl.set($("#c11"), { autoAlpha: 1 }, s);
      const a = $("#c11a"), ach = $$("#c11a .ch"), chs = $$("#c11b .ch");
      tl.set(chs, { autoAlpha: 0, scale: 1, y: 0 }, 0.002);
      tl.set(a, { autoAlpha: 0, x: 0, y: 0, scale: 1, rotation: 0, skewX: 0 }, 0.003);
      tl.set(ach, { autoAlpha: 1, x: 0, y: 0, scale: 1, rotation: 0 }, 0.0031);
      const hit = s + 0.3;
      if (k === "b") {
        // 一字一拳: 每個字從左右交替揍進來, 每個字都震一下, 最後的「!」最大力
        tl.set(a, { autoAlpha: 1 }, s);
        tl.set(ach, { autoAlpha: 0 }, s + 0.0001);
        ach.forEach((ch, i) => {
          const t = s + 0.04 + i * 0.07, last = i === ach.length - 1;
          fromTo(ch, { autoAlpha: 1, x: i % 2 ? 160 : -160, y: -60, scale: last ? 3.2 : 2.4, rotation: i % 2 ? 20 : -20 }, { x: 0, y: 0, scale: 1, rotation: 0, duration: 0.09, ease: "power4.in" }, t);
          shake(t + 0.09, last ? 22 : 8, last ? 10 : 3);
          cue("punch", t + 0.09, { id: "k11punch" + i });
        });
        fromTo(C.R, { z: 1.25 }, { z: 1, duration: 0.3, ease: "power3.out" }, s + 0.04 + (ach.length - 1) * 0.07 + 0.09);
      } else if (k === "c") {
        // 爆炸登場: 鋸齒爆炸框炸開, 字從中間彈出來, 之後一直微微顫抖
        tl.set($("#burst11"), { autoAlpha: 1, transformOrigin: "50% 50%" }, s);
        fromTo($("#burst11"), { scale: 0, rotation: -25 }, { scale: 1, rotation: 0, duration: 0.25, ease: "back.out(2.4)" }, s + 0.05);
        tl.to($("#burst11"), { rotation: 3, duration: 0.1, yoyo: true, repeat: 13, ease: "sine.inOut" }, s + 0.3);
        fromTo(a, { autoAlpha: 1, scale: 0 }, { scale: 1, duration: 0.35, ease: "elastic.out(1.2,0.45)" }, s + 0.12);
        flash(s + 0.12, 0.9, 0.15); shake(s + 0.12, 20, 10);
        tl.to(ach, { y: (i) => (i % 2 ? -4 : 4), duration: 0.05, yoyo: true, repeat: 21, ease: "none" }, s + 0.5);
        hide($("#burst11"), tq);
        cue("boom", s + 0.12);
      } else if (k === "d") {
        // 斜切橫幅: 紅色斜帶從左邊衝進來, 字從右邊斜著砸上去
        tl.set($("#band11"), { autoAlpha: 1 }, s);
        fromTo($("#band11"), { xPercent: -110 }, { xPercent: 0, duration: 0.18, ease: "power4.out" }, s + 0.02);
        fromTo(a, { autoAlpha: 1, x: 900, skewX: -30, rotation: -4 }, { x: 0, skewX: 0, duration: 0.16, ease: "power4.in" }, s + 0.14);
        tl.to(a, { skewX: 8, duration: 0.06, yoyo: true, repeat: 1 }, s + 0.3);
        shake(s + 0.3, 20, 10); flash(s + 0.3, 0.7, 0.12);
        fromTo(C.R, { z: 1.2 }, { z: 1, duration: 0.35, ease: "power3.out" }, s + 0.3);
        hide($("#band11"), tq);
        cue("slam", s + 0.3);
      } else {
        // 巨字砸下: 整句從超大砸到定位, 落地白閃 + 大震 + 畫面一縮
        fromTo(a, { autoAlpha: 1, scale: 3.4, rotation: -6 }, { scale: 1, rotation: -2, duration: 0.24, ease: "power4.in" }, s + 0.06);
        flash(hit, 0.9, 0.18); shake(hit, 24, 12);
        fromTo(C.R, { z: 1.3 }, { z: 1, duration: 0.35, ease: "power3.out" }, hit);
        tl.to(a, { rotation: 0, duration: 0.3, ease: "back.out(3)" }, hit + 0.02);
        cue("stamp", hit, { id: "k11stamp" });
      }
      // 第二句一個字一個字跳出來
      fromTo(chs, { autoAlpha: 1, scale: 0 }, { scale: 1, duration: 0.12, stagger: 0.06, ease: "back.out(3)" }, s + 0.85);
      // 對話框從觀眾身上彈出來
      tl.set($("#q11"), { transformOrigin: "152px -40px" }, 0.004);
      fromTo($("#q11"), { autoAlpha: 1, scale: 0, rotation: -8 }, { scale: 1, rotation: 0, duration: 0.3, ease: "back.out(2.6)" }, tq + 0.1);
      tl.to($("#q11"), { rotation: 2, duration: 0.08, yoyo: true, repeat: 5 }, tq + 0.45);
      cue("pop", tq + 0.1, { id: "k11bubble" });
      hide([$("#c11"), $("#q11")], e);
    }

    // ===== K14 · 熱度條特寫「喔不!」→「要失控啦~~~」時拉回整個畫面, 正好觸發失控 + 強烈特效 =====
    let looseEnd = 7.7; // K15 定格在 K14 最後那一格
    {
      const s = starts.k14, k = pick("k14"), e = s + durs.k14;
      const tLoose = s + 1.4; // loose 片段 6.3 秒跳出「失控!」
      const tOut = s + 1.0;   // 「要失控啦~~~」出現, 鏡頭開始拉回
      tl.set(G.R, { x: 0, y: 0, w: 1280, h: 720, r: 0 }, s);
      shot("R", "loose", 4.9, 6.3, s, tLoose, { cx: 657, cy: 150, z: 2.4, f: 0 });
      tl.to(C.R, { z: 2.55, duration: 1.0, ease: "none" }, s + 0.001);
      tl.to(C.R, { cx: 640, cy: 360, z: 1, duration: 0.4, ease: "power3.inOut" }, tOut);
      // 熱度條外面一圈紅框閃
      tl.set($("#hfR"), { autoAlpha: 1 }, s);
      tl.to($("#hfR"), { opacity: 0.3, duration: 0.12, yoyo: true, repeat: 7 }, s + 0.05);
      hide($("#hfR"), tOut);
      shake(s + 0.15, 6, 4);
      // 字幕: 「喔不!」先出來, 「要失控啦~~~」跟著鏡頭拉回出現; 動態另有方案 k14cap
      const c = $("#c14"), ca = $("#c14a"), caCh = $$("#c14a .ch"), cb = $$("#c14b .ch"), sws = $$("#c14 .sw"), kc = pick("k14cap");
      const tilde = cb.slice(-3);
      tl.set(c, { autoAlpha: 1 }, s);
      tl.set(ca, { autoAlpha: 1, x: 0, y: 0, scale: 1, rotation: 0 }, 0.005);
      tl.set([...caCh, ...cb], { autoAlpha: 0, x: 0, y: 0, scale: 1, scaleX: 1, scaleY: 1, rotation: 0, skewX: 0, color: "", transformOrigin: "50% 80%" }, 0.0051);
      tl.set(sws, { autoAlpha: 0, y: 0, scale: 1 }, 0.0052);
      const end14 = s + durs.k14;
      if (kc === "b") {
        // 原地慌張亂跳: 每個字各跳各的, 「~~~」像橡皮筋越拉越長
        fromTo(caCh, { autoAlpha: 1, y: -80, scale: 0.4 }, { y: 0, scale: 1, duration: 0.25, stagger: 0.06, ease: "bounce.out" }, s + 0.12);
        tl.to(caCh, { y: -18, rotation: (i) => (i % 2 ? 12 : -12), duration: 0.11, yoyo: true, repeat: 7, stagger: 0.05, ease: "power1.out" }, s + 0.45);
        fromTo(cb, { autoAlpha: 1, y: 60, scale: 0 }, { y: 0, scale: 1, duration: 0.18, stagger: 0.04, ease: "back.out(3)" }, tOut);
        tl.to(cb.slice(0, 4), { y: (i) => -14 - (i % 2) * 10, rotation: (i) => (i % 2 ? 10 : -10), duration: 0.1, yoyo: true, repeat: 9, stagger: 0.04, ease: "power1.out" }, tOut + 0.25);
        tl.set(tilde, { transformOrigin: "0% 50%" }, tOut + 0.001);
        tl.to(tilde, { scaleX: 2.2, x: (i) => i * 34, duration: 0.6, ease: "elastic.out(1,0.4)" }, tOut + 0.35);
      } else if (kc === "c") {
        // 越叫越大聲: 「喔不!」一抖一抖越變越大, 「要失控啦~~~」一個字一個字轉著飛進來, 紅黃閃
        fromTo(caCh, { autoAlpha: 1, scale: 0.6 }, { scale: 1, duration: 0.12, stagger: 0.03, ease: "back.out(3)" }, s + 0.12);
        tl.to(ca, { scale: 1.45, duration: 0.85, ease: "power1.in" }, s + 0.25);
        tl.to(ca, { x: 4, y: -2, duration: 0.03, yoyo: true, repeat: 27, ease: "none" }, s + 0.25);
        tl.to(ca, { scale: 1, x: 0, y: 0, duration: 0.15, ease: "power2.out" }, tOut);
        fromTo(cb, { autoAlpha: 1, scale: 3, rotation: (i) => (i % 2 ? 200 : -200), y: -120 }, { scale: 1, rotation: 0, y: 0, duration: 0.25, stagger: 0.05, ease: "power3.out" }, tOut);
        tl.to(cb, { color: GOLD, duration: 0.01, yoyo: true, repeat: 11, repeatDelay: 0.09, stagger: 0.03 }, tOut + 0.45);
        tl.to(cb, { x: (i) => (i % 2 ? 3 : -3), duration: 0.04, yoyo: true, repeat: 15, ease: "none" }, tOut + 0.45);
      } else if (kc === "d") {
        // 融化: 冒冷汗, 字一個個軟掉往下垂, 「~~~」像水波一樣流
        fromTo(caCh, { autoAlpha: 1, scale: 1.6 }, { scale: 1, duration: 0.18, stagger: 0.04, ease: "back.out(2.5)" }, s + 0.12);
        tl.set(sws, { autoAlpha: 1 }, s + 0.35);
        fromTo(sws, { y: -10, scale: 0.3 }, { y: 26, scale: 1, duration: 0.5, stagger: 0.12, ease: "power2.in" }, s + 0.35);
        tl.to(caCh, { scaleY: 0.82, scaleX: 1.12, y: 8, duration: 0.5, ease: "sine.inOut" }, s + 0.4);
        fromTo(cb, { autoAlpha: 1, y: -50, scale: 0.4 }, { y: 0, scale: 1, duration: 0.2, stagger: 0.05, ease: "back.out(2)" }, tOut);
        tl.to(cb.slice(0, 4), { scaleY: 1.3, scaleX: 0.85, y: 12, skewX: (i) => (i % 2 ? 10 : -10), duration: 0.35, stagger: 0.08, ease: "sine.inOut", yoyo: true, repeat: 2 }, tOut + 0.3);
        tl.to(tilde, { y: -12, duration: 0.15, yoyo: true, repeat: 9, stagger: 0.08, ease: "sine.inOut" }, tOut + 0.3);
      } else {
        // 抖抖抖: 「喔不!」嚇一跳彈出來還冒冷汗, 「要失控啦~~~」整句發抖, 「~~~」波浪一直滾
        fromTo(caCh, { autoAlpha: 1, scale: 2.4, rotation: (i) => (i % 2 ? 15 : -15) }, { scale: 1, rotation: 0, duration: 0.2, stagger: 0.05, ease: "back.out(3)" }, s + 0.12);
        tl.set(sws, { autoAlpha: 1 }, s + 0.4);
        fromTo(sws, { scale: 0 }, { scale: 1, duration: 0.15, stagger: 0.1, ease: "back.out(3)" }, s + 0.4);
        tl.to(caCh, { x: (i) => (i % 2 ? 3 : -3), duration: 0.035, yoyo: true, repeat: 15, ease: "none" }, s + 0.4);
        fromTo(cb, { autoAlpha: 1, scale: 0, y: 20 }, { scale: 1, y: 0, duration: 0.12, stagger: 0.05, ease: "back.out(3)" }, tOut);
        tl.to(cb.slice(0, 4), { x: (i) => (i % 2 ? 4 : -4), rotation: (i) => (i % 2 ? 4 : -4), duration: 0.04, yoyo: true, repeat: 19, ease: "none" }, tOut + 0.3);
        tl.to(tilde, { y: -14, duration: 0.12, yoyo: true, repeat: 11, stagger: 0.06, ease: "sine.inOut" }, tOut + 0.3);
      }
      cue("uhoh", s + 0.15); cue("zoomout", tOut);
      const fx = $("#fx14"), Q = (c) => fx.querySelector(c), QA = (c) => [...fx.querySelectorAll(c)];
      tl.set([Q(".shk"), Q(".bst"), Q(".emb"), Q(".flm")], { opacity: 0 }, 0);
      tl.set(QA(".rg"), { scale: 0.2, opacity: 1, transformOrigin: "50% 50%" }, 0);
      tl.set(QA(".em"), { x: 0, y: 0, opacity: 1 }, 0);
      tl.set(Q(".flm"), { y: 260 }, 0);
      tl.set(QA(".fl"), { scaleY: 1, transformOrigin: "50% 100%" }, 0);
      tl.set(Q(".spd"), { rotation: 0, svgOrigin: "640 300" }, 0);
      tl.set(fx, { autoAlpha: 1 }, tLoose);
      if (k === "b") {
        // 漫畫衝擊: 鏡頭猛推到「失控!」招牌, 背後集中線轉動, 白閃 + 大震, 紅色暗角
        shot("R", "loose", 6.3, 6.3 + (e - tLoose), tLoose, e);
        tl.set(C.R, { cx: 640, cy: 300, z: 1.75 }, tLoose + 0.0001);
        tl.to(C.R, { z: 1.25, duration: e - tLoose - 0.01, ease: "power2.out" }, tLoose + 0.001);
        tl.set(Q(".bst"), { opacity: 1 }, tLoose);
        tl.to(Q(".spd"), { rotation: 8, duration: e - tLoose, ease: "none" }, tLoose + 0.001);
        flash(tLoose, 1, 0.2); shake(tLoose, 26, 12); shake(tLoose + 0.6, 14, 6);
        tl.set($("#redv"), { autoAlpha: 0.9 }, tLoose); tl.to($("#redv"), { autoAlpha: 0.5, duration: 0.5 }, tLoose + 0.01);
        looseEnd = 6.3 + (e - tLoose);
        cue("crash", tLoose);
      } else if (k === "c") {
        // 頓格 + 慢動作: 觸發那一格停住、黑白反轉閃兩下, 接著慢動作播下去, 底下火星往上竄
        const hold = 0.35, slow = 0.5;
        seg("R", "loose", 6.3, 6.3, tLoose, tLoose + hold);
        seg("R", "loose", 6.3, 6.3 + (e - tLoose - hold) * slow, tLoose + hold, e);
        // 反色要硬切 (補間會經過 invert(0.5) 變成一片灰)
        [[0, "invert(1) contrast(1.6)"], [0.07, "contrast(1.3)"], [0.15, "invert(1) contrast(1.6)"], [0.22, "contrast(1.3)"], [hold, "none"]].forEach(([t, f]) => tl.set($("#world"), { filter: f }, tLoose + t));
        tl.to(C.R, { z: 1.15, duration: e - tLoose - 0.01, ease: "power1.out" }, tLoose + 0.001);
        tl.set(Q(".emb"), { opacity: 1 }, tLoose);
        tl.to(QA(".em"), { y: (i) => -820 - (i % 5) * 60, x: (i) => ((i * 13) % 60) - 30, opacity: 0.2, duration: 1.0, stagger: 0.01, ease: "power1.in" }, tLoose);
        tl.set($("#redv"), { autoAlpha: 0.7 }, tLoose + hold);
        shake(tLoose + hold, 20, 10);
        looseEnd = 6.3 + (e - tLoose - hold) * slow;
        cue("hitstop", tLoose); cue("crash", tLoose + hold, { id: "k14crash" });
      } else if (k === "d") {
        // 火焰邊框: 火從畫面底部與兩側竄上來一直燒, 紅光一陣一陣, 畫面跟著節奏震
        shot("R", "loose", 6.3, 6.3 + (e - tLoose), tLoose, e);
        tl.set(Q(".flm"), { opacity: 1 }, tLoose);
        tl.to(Q(".flm"), { y: 0, duration: 0.25, ease: "power3.out" }, tLoose);
        tl.to(QA(".fl"), { scaleY: 1.25, duration: 0.09, yoyo: true, repeat: 13, stagger: 0.01, ease: "sine.inOut" }, tLoose + 0.05);
        tl.to($("#redt"), { autoAlpha: 0.3, duration: 0.18, yoyo: true, repeat: 6 }, tLoose);
        [0, 0.4, 0.8, 1.2].forEach((t, i) => shake(tLoose + t, i ? 12 : 24, 6));
        flash(tLoose, 0.8, 0.15);
        looseEnd = 6.3 + (e - tLoose);
        cue("fire", tLoose);
      } else {
        // 衝擊波: 從「失控!」招牌炸出三圈衝擊波, 紅光脈動, 畫面猛縮再放
        shot("R", "loose", 6.3, 6.3 + (e - tLoose), tLoose, e);
        tl.set(Q(".shk"), { opacity: 1 }, tLoose);
        QA(".rg").forEach((r, i) => fromTo(r, { scale: 0.2, opacity: 1 }, { scale: 9, opacity: 0, duration: 0.7, ease: "power2.out" }, tLoose + i * 0.14));
        flash(tLoose, 1, 0.22); shake(tLoose, 28, 14);
        fromTo(C.R, { z: 1.35 }, { z: 1.05, duration: 0.5, ease: "back.out(2)" }, tLoose + 0.001);
        tl.to($("#redt"), { autoAlpha: 0.35, duration: 0.16, yoyo: true, repeat: 5 }, tLoose + 0.05);
        looseEnd = 6.3 + (e - tLoose);
        cue("shock", tLoose);
      }
      hide([c, fx, $("#redv"), $("#redt")], e);
      tl.set($("#world"), { filter: "none" }, e);
    }

    // ===== K15 · 收尾: 定格在失控畫面, 遊戲的紅布幕拉上 (不跳收場彈窗、不拉開、不掛招牌), 兩大標籤打在正中間 =====
    // 布幕與「恭喜過關」招牌用遊戲自己的畫法 (finart.js, tools/finart.mjs 產生); 合起來後跑馬燈燈泡一直繞
    {
      const s = starts.k15, k = pick("k15"), e = s + durs.k15;
      seg("R", "loose", looseEnd, looseEnd, s, e + 0.1);
      tl.set(C.R, { cx: 640, cy: 360, z: 1, f: 0 }, s);
      tl.set($("#world"), { skewX: 0, x: 0 }, s);
      tl.set(FIN, { t: -1 }, 0);
      tl.set($("#fin"), { autoAlpha: 1 }, s);
      fromTo(FIN, { t: 0 }, { t: durs.k15, duration: durs.k15, ease: "none" }, s + 0.0001);
      cue("curtain", s);
      const tL = $("#tagL"), tR = $("#tagR"), pl = $("#pls");
      // 跟開頭同一個「+」: 先把 K2 拉成分隔線的樣子還原
      tl.set($("#plsH"), { scaleX: 1 }, s);
      tl.set($("#plsV"), { top: -48, height: 96, width: 26, left: -13 }, s);
      const Y = 360, T0 = s + 0.7; // 布幕合起來後, 兩個標籤打在畫面正中間
      if (k === "b") {
        // 從左右兩邊滑進來, 中間「+」彈出
        fromTo(tL, { autoAlpha: 1, x: -400, y: Y, scale: 1, rotation: 0, rotationX: 0 }, { x: TAGPOS.L[0], duration: 0.4, ease: "back.out(1.4)" }, T0);
        fromTo(tR, { autoAlpha: 1, x: 1700, y: Y, scale: 1, rotation: 0, rotationX: 0 }, { x: TAGPOS.R[0], duration: 0.4, ease: "back.out(1.4)" }, T0);
        fromTo(pl, { autoAlpha: 1, x: PLUS[0], y: Y, scale: 0 }, { scale: 1, duration: 0.25, ease: "back.out(3)" }, T0 + 0.4);
        cue("whoosh", T0, { id: "k15whoosh" }); cue("pop", T0 + 0.4, { id: "k15pop" });
      } else if (k === "c") {
        // 跟開頭呼應: 兩個標籤翻轉立起
        fromTo(tL, { autoAlpha: 1, x: TAGPOS.L[0], y: Y, rotationX: -90, scale: 1, rotation: 0 }, { rotationX: 0, duration: 0.45, ease: "back.out(2)" }, T0);
        fromTo(tR, { autoAlpha: 1, x: TAGPOS.R[0], y: Y, rotationX: -90, scale: 1, rotation: 0 }, { rotationX: 0, duration: 0.45, ease: "back.out(2)" }, T0 + 0.35);
        fromTo(pl, { autoAlpha: 1, x: PLUS[0], y: Y, scale: 0 }, { scale: 1, duration: 0.25, ease: "back.out(3)" }, T0 + 0.75);
        cue("flip", T0 + 0.05, { id: "k15flip1" }); cue("flip", T0 + 0.4, { id: "k15flip2" });
      } else {
        // 一前一後從上方砸下來, 中間「+」
        fromTo(tL, { autoAlpha: 1, x: TAGPOS.L[0], y: Y, scale: 2.6, rotation: -8, rotationX: 0 }, { scale: 1, rotation: -3, duration: 0.28, ease: "power4.in" }, T0);
        fromTo(tR, { autoAlpha: 1, x: TAGPOS.R[0], y: Y, scale: 2.6, rotation: 8, rotationX: 0 }, { scale: 1, rotation: 3, duration: 0.28, ease: "power4.in" }, T0 + 0.45);
        fromTo(pl, { autoAlpha: 1, x: PLUS[0], y: Y, scale: 0 }, { scale: 1, duration: 0.2, ease: "back.out(3)" }, T0 + 0.8);
        shake(T0 + 0.28, 14); shake(T0 + 0.73, 14);
        cue("stamp", T0 + 0.28, { id: "k15stamp1" }); cue("stamp", T0 + 0.73, { id: "k15stamp2" });
      }
    }

    tl.set({}, {}, total);
    tl.timeScale(SPEED).paused(false);
    const out = gsap.timeline({ paused: true, onUpdate: drawAll });
    out.add(tl, 0);
    drawAll();
    const fast = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v / SPEED]));
    return {
      tl: out, total: total / SPEED, starts: fast(starts), durs: fast(durs), film,
      reel: reel.map((r) => ({ clip: r.clip, f0: r.f0, f1: r.f1 })),
      sfx: sfx.map((c) => ({ ...c, t: c.t / SPEED })),
      // 渲染工具每次 seek 後等這個: 每個畫布的影片跳到那一格並畫好
      // 審閱頁: 播放器換掉時不再收「格解好了」的通知
      dispose: () => WAIT.delete(onDecoded),
      settle: async () => { drawAll(); while (pending.size) { const ps = [...pending]; pending.clear(); await Promise.all(ps); } },
    };
  }

  root.VID = { FORMATS, size, KEYFRAMES, OPTIONS, SPEED, CSS, FONT_SAMPLE, fontsFor, build };
})(window);
