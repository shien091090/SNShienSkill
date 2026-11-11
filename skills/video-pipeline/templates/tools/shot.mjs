// node tools/shot.mjs '<picks JSON>' out-prefix t1 [t2 ...]
// Still frames at the given seconds (out-prefix_<t>.png), for checking a keyframe option before publishing.
import { openFilm } from './env.mjs';

const [,, picks = '{}', prefix, ...ts] = process.argv;
if (!prefix || !ts.length) { console.error("usage: node tools/shot.mjs '<picks JSON>' out-prefix t1 [t2 ...]"); process.exit(2); }
const { b, p } = await openFilm(picks);
for (const t of ts) {
  await p.evaluate((x) => { FILM.tl.seek(x, false); }, +t);
  await p.screenshot({ path: `${prefix}_${t}.png` });
}
await b.close();
console.log('shots:', ts.join(', '));
