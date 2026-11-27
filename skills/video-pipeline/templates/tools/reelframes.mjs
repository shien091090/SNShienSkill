// node tools/reelframes.mjs — 列出影片 (所有方案) 用到的遊戲片段格數範圍, 寫 .cache/reelframes.json
// 每個關鍵幀的方案 a/b/c/d 各組一次 (方案只影響自己那一幀的鏡頭), 取聯集; 格數是 60fps 的格
import fs from 'fs';
import path from 'path';
import { openFilm, ROOT } from './env.mjs';
const { b, p } = await openFilm('{}');
const ranges = await p.evaluate(() => {
  const out = {};
  for (const o of ['a', 'b', 'c', 'd']) {
    const pk = Object.fromEntries(Object.entries(VID.OPTIONS).map(([k, v]) => [k, v.includes(o) ? o : v[0]]));
    const host = document.createElement('div'); document.body.appendChild(host);
    const f = VID.build(host, pk);
    for (const r of f.reel) (out[r.clip] = out[r.clip] || []).push([Math.min(r.f0, r.f1), Math.max(r.f0, r.f1)]);
    f.tl.kill(); host.remove();
  }
  return out;
});
await b.close();
fs.mkdirSync(path.join(ROOT, '.cache'), { recursive: true });
fs.writeFileSync(path.join(ROOT, '.cache', 'reelframes.json'), JSON.stringify(ranges));
let tot = 0;
for (const [k, rs] of Object.entries(ranges)) { const s = new Set(); for (const [a, c] of rs) for (let j = Math.floor(a / 2); j <= Math.ceil(c / 2); j++) s.add(j); tot += s.size; console.log(k, s.size); }
console.log('total 30fps frames', tot);
