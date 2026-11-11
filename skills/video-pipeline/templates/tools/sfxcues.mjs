// node tools/sfxcues.mjs audio/cues.json ['<picks JSON>']
// Reads the film's sound cues (the cue() calls in film.js) and writes them with stable ids "<id>@<frame at 60 fps>".
// Copy the result to audio/cues.base.json when the sound options are made, so later retimes can map back by order.
import fs from 'fs';
import { openFilm } from './env.mjs';

const [,, out, picks = '{}'] = process.argv;
if (!out) { console.error('usage: node tools/sfxcues.mjs out.json'); process.exit(2); }
const FPS = 60;
const { b, p } = await openFilm(picks);
const { total, sfx } = await p.evaluate(() => ({ total: FILM.total, sfx: FILM.sfx }));
await b.close();
const events = sfx
  .map(({ t, kind, dur, id, ...o }) => ({ t: +t.toFixed(3), f: +(t * FPS).toFixed(2), kind, ...(dur ? { dur } : {}), id: id + '@' + (t * FPS).toFixed(0), ...o }))
  .sort((a, b) => a.t - b.t);
fs.writeFileSync(out, JSON.stringify({ fps: FPS, total: +total.toFixed(3), events }, null, 1));
console.log(events.length, 'cues,', total.toFixed(2), 's');
