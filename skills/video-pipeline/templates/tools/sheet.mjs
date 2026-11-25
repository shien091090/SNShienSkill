// node tools/sheet.mjs out.jpg img1 img2 ... — contact sheet (4 per row, 360px tiles) for quick self-review
import { execFileSync } from 'child_process';
import fs from 'fs';
const cfg = JSON.parse(fs.readFileSync(new URL('../video.config.json', import.meta.url)));
const [,, out, ...imgs] = process.argv;
const n = imgs.length, cols = Math.min(4, n), rows = Math.ceil(n / cols);
const args = []; imgs.forEach((f) => args.push('-i', f));
const pad = cols * rows - n;
let fl = imgs.map((_, i) => `[${i}:v]scale=360:360[v${i}]`).join(';');
for (let i = 0; i < pad; i++) fl += `;color=c=gray:s=360x360:d=1[p${i}]`;
const ins = [...imgs.map((_, i) => `[v${i}]`), ...Array.from({ length: pad }, (_, i) => `[p${i}]`)].join('');
const layout = Array.from({ length: cols * rows }, (_, i) => `${(i % cols) * 362}_${Math.floor(i / cols) * 362}`).join('|');
fl += `;${ins}xstack=inputs=${cols * rows}:layout=${layout}:fill=black`;
execFileSync(cfg.ffmpeg, ['-y', '-v', 'error', ...args, '-filter_complex', fl, '-frames:v', '1', '-q:v', '3', out]);
console.log(out);
