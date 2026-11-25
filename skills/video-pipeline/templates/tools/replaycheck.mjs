// node tools/replaycheck.mjs '<picks>' [fps=15] — plays the film twice the way the review page loops (forward, back to 0,
// forward) and reports checkpoints whose second-pass frame visibly differs from the first (PSNR < 45 dB; anti-aliasing
// noise is ~60+). Differing pairs are saved to renders/replay/<t>_1.png and _2.png. Exit 1 if anything differs.
import { openFilm, FFMPEG, ROOT } from './env.mjs';
import { spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';
const [,, picks = '{}', fps = '15'] = process.argv;
const { b, p } = await openFilm(picks);
const total = await p.evaluate(() => FILM.total);
const checks = []; for (let t = 0.25; t < total; t += 0.5) checks.push(+t.toFixed(2));
const step = 1 / +fps;
const seek = (t) => p.evaluate(async (x) => { FILM.tl.seek(x, false); if (FILM.settle) await FILM.settle(); }, t); // returns nothing: a returned timeline would be serialized and hang
async function pass() {
  const shots = {};
  let ci = 0;
  for (let t = 0; t <= total + 1e-6 && ci < checks.length; t += step) {
    if (t + step > checks[ci]) { await seek(checks[ci]); shots[checks[ci]] = Buffer.from(await p.screenshot()); ci++; }
    else await seek(t);
  }
  await seek(total);
  return shots;
}
const a = await pass();
await seek(0);
const c = await pass();
await b.close();
const dir = path.join(ROOT, 'renders', 'replay');
fs.mkdirSync(dir, { recursive: true });
const bad = [];
for (const t of checks) {
  if (a[t].equals(c[t])) continue;
  const f1 = path.join(dir, `${t}_1.png`), f2 = path.join(dir, `${t}_2.png`);
  fs.writeFileSync(f1, a[t]); fs.writeFileSync(f2, c[t]);
  const r = spawnSync(FFMPEG, ['-i', f1, '-i', f2, '-lavfi', 'psnr', '-f', 'null', '-'], { encoding: 'utf8' });
  const m = /average:(\S+)/.exec(r.stderr || '');
  const db = m ? (m[1] === 'inf' ? Infinity : +m[1]) : 0;
  if (db < 45) bad.push(`${t}s (${db.toFixed(1)} dB)`);
}
console.log(bad.length ? 'replay differs at: ' + bad.join(', ') : 'replay matches first play');
process.exit(bad.length ? 1 : 0);
