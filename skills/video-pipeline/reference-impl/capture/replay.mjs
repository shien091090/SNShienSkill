// 把錄下的操作紀錄在無頭瀏覽器重播成影片 (不看電腦快慢, 每一格都照遊戲步數算):
//   node replay.mjs takes/<紀錄>.json preview                      -> takes/<紀錄>-preview.mp4 (640×360, 15fps, 左上角時間碼, 用來找片段)
//   node replay.mjs takes/<紀錄>.json clip <起秒> <迄秒> <輸出.mp4> [倍率=2]
//                                                                    -> 60fps, 1280×720 × 倍率, 旁邊寫 <輸出>.sfx.json (遊戲音效事件, 秒數從片段開頭算)
// 重播時每 10 秒比對一次遊戲狀態, 跟錄製當下不同會警告 (代表重播走樣了)
import http from 'http';
import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CFG = JSON.parse(fs.readFileSync(path.join(HERE, 'config.json'), 'utf8'));
const puppeteer = createRequire(path.join(HERE, 'package.json'))('puppeteer-core');
const [,, takePath, mode = 'preview', a1, a2, outArg, scaleArg = '2'] = process.argv;
if (!takePath) { console.error('usage: node replay.mjs takes/<紀錄>.json preview | clip <起秒> <迄秒> <輸出.mp4> [倍率]'); process.exit(2); }
const log = JSON.parse(fs.readFileSync(takePath, 'utf8'));
const PREVIEW = mode === 'preview';
const from = PREVIEW ? 0 : Math.round(+a1 * 60), to = PREVIEW ? log.steps : Math.round(+a2 * 60);
const scale = PREVIEW ? 0.5 : +scaleArg;
const every = PREVIEW ? 4 : 1;
const out = PREVIEW ? takePath.replace(/\.json$/, '-preview.mp4') : outArg;
if (!out) { console.error('clip 要給輸出檔名'); process.exit(2); }

// 靜態伺服器 (跟 server.mjs 同樣的檔案, 但不收紀錄)
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png', '.json': 'application/json', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.wav': 'audio/wav' };
const srv = http.createServer((q, r) => {
  const f = path.join(HERE, decodeURIComponent(q.url.split('?')[0]));
  if (!f.startsWith(HERE) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(r);
}).listen(0);

const b = await puppeteer.launch({ executablePath: CFG.chrome, args: ['--autoplay-policy=no-user-gesture-required'] });
const p = await b.newPage();
await p.setViewport({ width: 1280, height: 720, deviceScaleFactor: scale });
p.on('pageerror', (e) => console.log('page error:', e.message));
await p.evaluateOnNewDocument(() => {
  window.requestAnimationFrame = () => 0;                     // 迴圈由這支程式一步一步推
  window.AudioContext = window.webkitAudioContext = undefined;  // 不出聲
});
await p.goto(`http://localhost:${srv.address().port}/game/index.html?replay&w=${log.w}&seed=${log.seed}`, { waitUntil: 'load' });
await p.waitForFunction('typeof window.__stepOnce === "function" && !document.getElementById("pvd-load")', { timeout: 60000, polling: 200 });
await p.evaluate((ev) => {
  window.__EV = ev; window.__ei = 0; window.__snd = [];
  const S = typeof Snd !== 'undefined' ? Snd : window.Snd;   // 遊戲的音效物件 (game.js 頂層 const)
  if (S) for (const fn of ['play', 'once']) if (S[fn]) { const o = S[fn].bind(S); S[fn] = function (n, ...x) { window.__snd.push([__steps, n]); try { return o(n, ...x); } catch (e) {} }; }
  window.__adv = (n) => {
    for (let j = 0; j < n; j++) {
      while (__ei < __EV.length && __EV[__ei][0] <= __steps) {
        const [, t, k] = __EV[__ei++];
        if (t === 'd') inputDown(k); else if (t === 'u') inputUp(k); else inputReset();
      }
      __stepOnce();
    }
    return __steps;
  };
}, log.ev);

const chk = new Map(log.chk.map(([s, h]) => [s, h]));
let bad = 0;
async function advance(n) {
  // 一次最多推到下一個比對點, 到了就比對
  while (n > 0) {
    const cur = await p.evaluate(() => __steps);
    const next = Math.ceil((cur + 1) / 600) * 600;
    const k = Math.min(n, next - cur);
    const now = await p.evaluate((k) => __adv(k), k);
    n -= k;
    if (chk.has(now)) {
      const h = await p.evaluate(() => __hash());
      if (h !== chk.get(now)) { bad++; if (bad <= 3) console.log(`警告: 第 ${(now / 60).toFixed(0)} 秒的遊戲狀態跟錄製時不同, 之後的畫面可能走樣`); }
    }
  }
}

const fps = 60 / every;
const ff = spawn(CFG.ffmpeg, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
  '-c:v', 'libx264', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-crf', PREVIEW ? '23' : '12', '-preset', PREVIEW ? 'veryfast' : 'medium', '-movflags', '+faststart', out],
  { stdio: ['pipe', 'inherit', 'inherit'] });

await advance(from);
const total = Math.floor((to - from) / every);
for (let i = 0; i < total; i++) {
  const jpg = await p.evaluate((pv) => {
    __draw();
    if (pv) {   // 時間碼: 分:秒.十分之一
      const c = __ctx, t = __steps / 60;
      c.setTransform(1, 0, 0, 1, 0, 0);
      c.font = 'bold 22px system-ui'; c.fillStyle = 'rgba(0,0,0,.6)'; c.fillRect(0, 0, 118, 30);
      c.fillStyle = '#ff0'; c.fillText(Math.floor(t / 60) + ':' + (t % 60).toFixed(1).padStart(4, '0'), 8, 23);
    }
    return __canvas.toDataURL('image/jpeg', pv ? 0.8 : 0.95);
  }, PREVIEW);
  if (!ff.stdin.write(Buffer.from(jpg.split(',')[1], 'base64'))) await new Promise((r) => ff.stdin.once('drain', r));
  await advance(every);
  if (i % 600 === 0) process.stdout.write(`\r${i}/${total}`);
}
ff.stdin.end();
await new Promise((r) => ff.on('close', r));
if (!PREVIEW) {
  const snd = (await p.evaluate(() => __snd)).filter(([s]) => s >= from && s < to).map(([s, n]) => ({ t: +((s - from) / 60).toFixed(4), name: n }));
  fs.writeFileSync(out.replace(/\.mp4$/, '') + '.sfx.json', JSON.stringify(snd, null, 1));
}
console.log(`\ndone ${out}  ${((to - from) / 60).toFixed(2)} 秒${bad ? `  (狀態比對不合 ${bad} 次)` : '  (重播與錄製一致)'}`);
await b.close();
srv.close();
