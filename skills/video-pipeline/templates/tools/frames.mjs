// node tools/frames.mjs — 審閱頁用的遊戲畫面: 影片 (所有方案) 會用到的格, 轉成 640 寬 30fps 的 JPEG, 每個片段打包成一個檔
//   live/frames/<id>.jpg   用到的格的 JPEG 接在一起 (副檔名用 .jpg: 審閱頁發布只收常見檔案類型; 檔頭就是第一格, 本身也是一張合法圖片)
//   live/framedata.js      每格在 .jpg 裡的位置: FRAMEDATA[id] = [[30fps 格號, 起點, 長度], ...]
// 審閱頁不用 <video>: 影片元素跳格慢、同時太多個瀏覽器會停掉, 會卡頓、整段不見。圖片格一定畫得出來。
// 成片不受影響 (渲染用 media/ 的 2560 寬 60fps 影片)。先跑 tools/reelframes.mjs 列出用到的格。
import fs from 'fs';
import path from 'path';
import { spawnSync } from 'child_process';
import { FFMPEG, ROOT } from './env.mjs';

const SRC = process.env.CLIP_SRC || path.join(ROOT, 'clips-src');
const RF = path.join(ROOT, '.cache', 'reelframes.json');
if (!fs.existsSync(RF)) { console.error('先跑 node tools/reelframes.mjs'); process.exit(1); }
const ranges = JSON.parse(fs.readFileSync(RF, 'utf8'));
const W = 640, Q = '6'; // 640 寬: 審閱頁看得懂就好 (使用者同意審閱頁可以糊), 檔案小、解碼快
const out = path.join(ROOT, 'live', 'frames');
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });
const data = {};
let total = 0;
for (const [id, rs] of Object.entries(ranges)) {
  const src = path.join(SRC, id + '.mp4');
  if (!fs.existsSync(src)) { console.error('找不到片段 ' + src + ' (設 CLIP_SRC 指到片段資料夾)'); process.exit(1); }
  const tmp = path.join(ROOT, '.cache', 'fr', id);
  const mark = path.join(tmp, '.mark'), want = `${W}q${Q}:${fs.statSync(src).mtimeMs}`;
  if (!fs.existsSync(mark) || fs.readFileSync(mark, 'utf8') !== want) {
    fs.rmSync(tmp, { recursive: true, force: true }); fs.mkdirSync(tmp, { recursive: true });
    const r = spawnSync(FFMPEG, ['-y', '-loglevel', 'error', '-i', src, '-vf', `fps=30,scale=${W}:${W * 9 / 16}`, '-q:v', Q, '-start_number', '0', path.join(tmp, '%05d.jpg')], { stdio: 'inherit' });
    if (r.status) { console.error('ffmpeg 失敗: ' + id); process.exit(1); }
    fs.writeFileSync(mark, want);
  }
  const js = new Set();
  for (const [a, b] of rs) for (let j = Math.floor(a / 2); j <= Math.ceil(b / 2); j++) js.add(j);
  const bufs = [], idx = [];
  let off = 0;
  for (const j of [...js].sort((x, y) => x - y)) {
    const f = path.join(tmp, String(j).padStart(5, '0') + '.jpg');
    if (!fs.existsSync(f)) continue; // 超過片段尾端
    const buf = fs.readFileSync(f);
    bufs.push(buf); idx.push([j, off, buf.length]); off += buf.length;
  }
  fs.writeFileSync(path.join(out, id + '.jpg'), Buffer.concat(bufs));
  data[id] = idx; total += off;
  console.log(id, idx.length, 'frames', (off / 1024 / 1024).toFixed(1) + 'MB');
}
fs.writeFileSync(path.join(ROOT, 'live', 'framedata.js'), '// tools/frames.mjs 產生: 審閱頁遊戲畫面每格在 frames/<id>.jpg 的位置 [30fps 格號, 起點, 長度]\nwindow.FRAMEDATA = ' + JSON.stringify(data) + ';\n');
console.log('total', (total / 1024 / 1024).toFixed(1) + 'MB');
