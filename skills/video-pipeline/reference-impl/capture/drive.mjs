// node capture/drive.mjs <script.mjs> [outDir]
// Plays the real game (capture/game, a copy with step/render hooks) in headless Chrome under a fake clock,
// driven by a script of inputs, and saves one JPG per 2 game steps (30 fps) to outDir while recording is on.
// Without outDir it only runs the script (for probing positions with g.log()).
import http from 'http';
import fs from 'fs';
import path from 'path';
import { pathToFileURL } from 'url';
import { puppeteer, CFG, ROOT } from '../tools/env.mjs';

const [,, scriptPath, outDir] = process.argv;
const GAME = path.join(ROOT, 'capture', 'game');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png', '.json': 'application/json', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.wav': 'audio/wav' };
const srv = http.createServer((q, r) => {
  const f = path.join(GAME, decodeURIComponent(q.url.split('?')[0]));
  if (!f.startsWith(GAME) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(r);
}).listen(0);
const port = srv.address().port;

const b = await puppeteer.launch({ executablePath: CFG.chrome, args: ['--autoplay-policy=no-user-gesture-required'] });
const p = await b.newPage();
await p.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
p.on('pageerror', (e) => console.log('page error:', e.message));
p.on('console', (m) => { if (m.type() === 'error') console.log('console:', m.text()); });
await p.evaluateOnNewDocument(() => {
  let clock = 0;
  window.__clock = () => clock;
  window.__noTut = true;   // 不畫新手教學泡泡(遊戲邏輯照跑, 腳本輸入不受影響)
  window.__adv = (ms) => { clock += ms; };
  performance.now = () => clock;
  Date.now = () => 1.7e12 + clock;
  window.requestAnimationFrame = () => 0;   // the game loop is driven by __step / __render only
  window.AudioContext = window.webkitAudioContext = undefined;
});
await p.goto(`http://localhost:${port}/index.html`, { waitUntil: 'load' });
await p.waitForFunction('typeof window.__step === "function" && !document.getElementById("pvd-load")', { timeout: 60000, polling: 200 });

let n = 0, rec = false, shot = 0;
const evlog = [];   // 遊戲發出的音效事件 (名稱、當下畫格), 給影片配遊戲原音用
// 音效事件: 包住 Sound.play 記下名稱 (錄影時 AudioContext 關掉, 不會真的出聲)
await p.evaluate(() => { window.__ev = []; const S = window.Sound; if (S && S.play) { const o = S.play.bind(S); S.play = (name, arg) => { window.__ev.push(name); try { return o(name, arg); } catch (e) {} }; } });
if (outDir) fs.mkdirSync(outDir, { recursive: true });
const g = {
  async steps(k) {
    for (let i = 0; i < k; i++) {
      const ev = await p.evaluate(() => { __adv(1000 / 60); __tick(1 / 60); __step(); const e = window.__ev || []; window.__ev = []; return e; });
      n++;
      if (rec) for (const name of ev) evlog.push({ name, shot, n });
      if (rec && outDir && n % 2 === 0) {
        const data = await p.evaluate(() => { __render(); return document.getElementById('c').toDataURL('image/jpeg', 0.92); });
        fs.writeFileSync(path.join(outDir, `f${String(shot++).padStart(4, '0')}.jpg`), Buffer.from(data.split(',')[1], 'base64'));
      }
    }
  },
  wait(k) { return g.steps(k); },
  down(k) { return p.evaluate((x) => inputDown(x), k); },
  up(k) { return p.evaluate((x) => inputUp(x), k); },
  async hold(keys, k) { for (const x of [].concat(keys)) await g.down(x); await g.steps(k); for (const x of [].concat(keys)) await g.up(x); },
  async jump(k = 20) { await g.down('up'); await g.steps(k); await g.up('up'); },
  key(code) { return p.keyboard.press(code); },
  state() { return p.evaluate(() => { const S = __S, P = S.P || {}; return { screen: S.screen, phase: S.phase, level: S.level, gen: S.gen, x: +(P.x || 0).toFixed(1), y: +(P.y || 0).toFixed(1), g: P.grounded }; }); },
  async log(tag = '') { console.log(n, tag, JSON.stringify(await g.state())); },
  record(on) { rec = on; },
  eval: (fn, ...a) => p.evaluate(fn, ...a),
  get frame() { return n; },
  get shots() { return shot; },
};
const script = (await import(pathToFileURL(path.resolve(scriptPath)).href)).default;
await script(g);
console.log('done, steps', n, 'shots', shot);
if (outDir) fs.writeFileSync(path.join(outDir, 'events.json'), JSON.stringify(evlog, null, 1));
await b.close();
srv.close();
