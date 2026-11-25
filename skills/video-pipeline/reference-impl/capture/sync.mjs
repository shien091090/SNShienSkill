// node sync.mjs — 把遊戲 (WebGame_DungeonZoo/release/game) 複製成 game/ 並改成錄按鍵版。遊戲更新後重跑一次。
// 注意: 遊戲改版後, 舊的錄製紀錄 (takes/*.json) 不保證能照原樣重播。
// 換遊戲時: SRC 改成該遊戲的 release/game 位置 (下面是馬戲團的本機路徑, 只是範例), 並重找每個改點的字串。
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = 'E:/Project/Game/WebGame_DungeonZoo/release/game';
const DST = path.join(HERE, 'game');
fs.rmSync(DST, { recursive: true, force: true });
fs.cpSync(SRC, DST, { recursive: true });

const must = (ok, what) => { if (!ok) { console.error('改不到: ' + what + ' (遊戲改版了? 要更新 sync.mjs)'); process.exit(1); } };

// index.html: 最先載入 rec.js
const ih = path.join(DST, 'index.html');
let html = fs.readFileSync(ih, 'utf8');
const canvasTag = /<canvas id="c"[^>]*><\/canvas>/;
must(canvasTag.test(html), 'index.html 的 canvas');
html = html.replace(canvasTag, (m) => m + '\n<script src="/rec.js"></script>');
fs.writeFileSync(ih, html);

// game.js: 遊戲邏輯亂數改固定種子; 可變時間迴圈換成固定 60 步/秒
const gj = path.join(DST, 'game.js');
let js = fs.readFileSync(gj, 'utf8');
const nRand = (js.match(/Math\.random\(\)/g) || []).length;
must(nRand > 0, 'game.js 的亂數');
js = js.replaceAll('Math.random()', '__rng()');
const cut = js.indexOf('let lastTs = 0;');
must(cut > 0, 'game.js 的遊戲迴圈');
js = js.slice(0, cut) + `// ── 錄按鍵版: 固定 60 步/秒 (dungeon-zoo/sync.mjs 換掉原本的可變時間迴圈) ──
(function () {
  const STEP = 1 / 60;
  const paused = () => !!(window.PVDX && PVDX.paused);
  if (!window.__REPLAY) {
    const oDown = inputDown, oUp = inputUp, oReset = inputReset;
    inputDown = function (k) { if (!paused()) __rec('d', k); return oDown(k); };
    inputUp = function (k) { __rec('u', k); return oUp(k); };
    inputReset = function () { __rec('r'); return oReset(); };
  }
  function hash() {
    let s; try { s = JSON.stringify([scene, G, S]); } catch (e) { s = String(scene); }
    let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return (h >>> 0).toString(16);
  }
  function step() {
    update(STEP); __steps++;
    if (__steps % 600 === 0 && window.__log) __log.chk.push([__steps, hash()]);
  }
  function draw() {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, CW, CH);
    render();
    if (window.PVDX && !window.__REPLAY) PVDX.draw(ctx);
  }
  window.__hash = hash; window.__stepOnce = step; window.__draw = draw; window.__ctx = ctx; window.__canvas = canvas;
  if (window.__REPLAY) return;
  let acc = 0, last = 0;
  function frame() {
    const t = __realNow();
    if (!last) last = t;
    acc += Math.min(t - last, 100); last = t;
    try {
      while (acc >= 1000 / 60) { acc -= 1000 / 60; if (!paused()) step(); }
      draw();
    } catch (err) { console.error(err); }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
`;
fs.writeFileSync(gj, js);
console.log(`game/ 已更新: 亂數 ${nRand} 處改固定種子, 迴圈改固定 60 步/秒`);
