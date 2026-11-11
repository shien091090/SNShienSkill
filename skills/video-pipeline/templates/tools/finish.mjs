// node tools/finish.mjs silent.mp4 audio.wav out.mp4 [lufs=-14] [tp=-1]
// Two-pass loudness normalisation of the final soundtrack, mux with the silent picture (video stream copied),
// then measure the result and check loudness, true peak and length. Exit code 1 when a check fails.
import { spawnSync } from 'child_process';
import { FFMPEG } from './env.mjs';

const [,, video, audio, out, lufsArg = '-14', tpArg = '-1'] = process.argv;
if (!out) { console.error('usage: node tools/finish.mjs silent.mp4 audio.wav out.mp4 [lufs] [tp]'); process.exit(2); }
const I = +lufsArg, TP = +tpArg;
// ffmpeg reports on stderr; spawnSync gives it back whatever the exit code
const ff = (args) => {
  const r = spawnSync(FFMPEG, ['-hide_banner', '-nostats', ...args], { encoding: 'utf8', maxBuffer: 1 << 26 });
  return r.stderr || '';
};
const loud = (file) => {
  const s = ff(['-i', file, '-af', `loudnorm=I=${I}:TP=${TP}:LRA=11:print_format=json`, '-f', 'null', '-']);
  return JSON.parse(s.slice(s.lastIndexOf('{'), s.lastIndexOf('}') + 1));
};
const duration = (file) => { const m = /Duration: (\d+):(\d+):([\d.]+)/.exec(ff(['-i', file])); return m ? +m[1] * 3600 + +m[2] * 60 + +m[3] : NaN; };

const m1 = loud(audio);
const af = `loudnorm=I=${I}:TP=${TP}:LRA=11:measured_I=${m1.input_i}:measured_TP=${m1.input_tp}:measured_LRA=${m1.input_lra}:measured_thresh=${m1.input_thresh}:offset=${m1.target_offset}:linear=true,aresample=48000`;
const err = ff(['-y', '-loglevel', 'error', '-i', video, '-i', audio, '-map', '0:v', '-map', '1:a', '-af', af, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-shortest', '-movflags', '+faststart', out]);
if (err.trim()) console.log(err.trim());

const m2 = loud(out);
const dv = duration(video), dout = duration(out);
const checks = [
  ['loudness', Math.abs(+m2.input_i - I) <= 1, `${m2.input_i} LUFS (target ${I})`],
  ['true peak', +m2.input_tp <= TP + 0.5, `${m2.input_tp} dBTP (ceiling ${TP})`],
  ['length', Math.abs(dout - dv) <= 0.1, `${dout.toFixed(2)} s (picture ${dv.toFixed(2)} s)`],
];
for (const [name, ok, msg] of checks) console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}: ${msg}`);
process.exit(checks.every((c) => c[1]) ? 0 : 1);
