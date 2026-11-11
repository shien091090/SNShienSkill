// node tools/renderfilm.mjs '<picks JSON>' out.mp4 [fps=30]
// Frame-accurate silent render: seeks the film's GSAP timeline frame by frame in headless Chrome and pipes
// JPEG screenshots into ffmpeg. The format comes from picks.fmt (see film.js FORMATS).
import { spawn } from 'child_process';
import { openFilm, FFMPEG } from './env.mjs';

const [,, picks = '{}', out, fpsArg = '30'] = process.argv;
if (!out) { console.error("usage: node tools/renderfilm.mjs '<picks JSON>' out.mp4 [fps]"); process.exit(2); }
const fps = +fpsArg;
const { b, p, W, H } = await openFilm(picks);
const total = await p.evaluate(() => FILM.total);
const n = Math.round(total * fps);
// JPEG frames are full-range BT.601. Browsers show untagged full-range video oversaturated
// (yellow #f5e291 came out #fff193), so convert to limited-range BT.709 and tag it.
const ff = spawn(FFMPEG, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
  '-vf', 'scale=in_range=pc:in_color_matrix=bt601:out_range=tv:out_color_matrix=bt709,format=yuv420p',
  '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
  '-c:v', 'libx264', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'medium', '-movflags', '+faststart', out],
  { stdio: ['pipe', 'inherit', 'inherit'] });
for (let f = 0; f < n; f++) {
  await p.evaluate((t) => { FILM.tl.seek(t, false); }, f / fps);
  const buf = await p.screenshot({ type: 'jpeg', quality: 95 });
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  if (f % 150 === 0) console.log(`${f}/${n}`);
}
ff.stdin.end();
await new Promise((r) => ff.on('close', r));
await b.close();
console.log('done', out, `${W}x${H}`, total.toFixed(2) + 's');
