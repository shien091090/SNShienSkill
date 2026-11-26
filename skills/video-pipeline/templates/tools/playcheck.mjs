// node tools/playcheck.mjs [起秒] [迄秒] [畫布選擇器] — 用本機 http 伺服器 + 限速網路 (約 32Mbps) 開審閱頁,
// 等片段下載完 (#loadmsg 消失), 從頭即時播放, 起迄秒之間每 100ms 取主播放器的畫布 (預設 #main 裡第一個 canvas):
// 報告黑畫面格數與「畫面沒變」的最長連續段。用來抓遊戲片段在審閱頁「第一次播全黑、快閃段停格」這類問題,
// 檔案協定的 pagecheck 抓不到 (沒有網路延遲)。黑畫面 > 0 就 exit 1; 停格超過該段鏡頭長度也是有問題, 要自己看報告
import http from 'http'; import fs from 'fs'; import path from 'path';
import { CFG, ROOT, puppeteer } from './env.mjs';
const [A, B] = [Number(process.argv[2] ?? 0), Number(process.argv[3] ?? 10)];
const SEL = process.argv[4] || '#main canvas';
const LIVE = path.join(ROOT, 'live');
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mp4': 'video/mp4', '.json': 'application/json', '.css': 'text/css' };
const srv = http.createServer((q, r) => {
  const f = path.join(LIVE, decodeURIComponent(q.url.split('?')[0]));
  if (!f.startsWith(LIVE) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(r);
}).listen(0);
const port = srv.address().port;
// 預設用渲染工具的無頭 Chrome; 設 PLAYCHECK_CHROME 指到一般 Chrome 可測一般瀏覽器的影片播放 (無頭版的影片播放不一定照實)
const b = await puppeteer.launch({ executablePath: process.env.PLAYCHECK_CHROME || CFG.chrome, headless: true, args: ['--autoplay-policy=no-user-gesture-required'] });
const p = await b.newPage(); await p.setViewport({ width: 1400, height: 900 });
const cdp = await p.createCDPSession();
await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 40, downloadThroughput: 4e6, uploadThroughput: 1e6 });
const t0 = Date.now();
await p.goto(`http://localhost:${port}/index.html`, { waitUntil: 'load' });
await p.waitForFunction(() => document.getElementById('loadmsg').hidden, { timeout: 180000 });
console.log('片段下載完', ((Date.now() - t0) / 1000).toFixed(1), '秒');
await new Promise((r) => setTimeout(r, 1500));
const samples = await p.evaluate(async (A, B, SEL) => {
  document.getElementById('replay').click();
  const cv = document.querySelector(SEL), tmp = document.createElement('canvas'); tmp.width = 64; tmp.height = 36;
  const x = tmp.getContext('2d', { willReadFrequently: true });
  const out = [];
  const start = performance.now();
  while (true) {
    const t = (performance.now() - start) / 1000;
    if (t > B) break;
    if (t >= A) {
      x.drawImage(cv, 0, 0, 64, 36);
      const d = x.getImageData(0, 0, 64, 36).data; let s = 0, h = 0;
      for (let i = 0; i < d.length; i += 4) { s += d[i] + d[i + 1] + d[i + 2]; h = (h * 31 + d[i] + d[i + 1]) >>> 0; }
      out.push([+t.toFixed(2), Math.round(s / (d.length / 4) / 3), h]);
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  return out;
}, A, B, SEL);
let black = 0, run = 1, worst = [0, 0];
for (let i = 0; i < samples.length; i++) {
  if (samples[i][1] < 8) black++;
  if (i && samples[i][2] === samples[i - 1][2]) { run++; if (run > worst[0]) worst = [run, samples[i - run + 1][0]]; } else run = 1;
}
console.log(`取樣 ${samples.length} 格, 黑畫面 ${black} 格, 畫面最長沒變 ${worst[0]} 格 (約 ${(worst[0] * 0.1).toFixed(1)} 秒, 從 ${worst[1]} 秒起)`);
await b.close(); srv.close();
if (black > 0) process.exit(1);
