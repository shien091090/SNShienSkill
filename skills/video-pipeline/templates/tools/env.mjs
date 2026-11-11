// Shared paths for the render tools. Everything is resolved from the video folder (one level above tools/)
// and from video.config.json there, which `node tools/setup.mjs` writes. No machine paths are hard-coded.
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const cfgPath = path.join(ROOT, 'video.config.json');
if (!fs.existsSync(cfgPath)) { console.error('video.config.json missing: run `node tools/setup.mjs` first'); process.exit(2); }
export const CFG = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
export const puppeteer = createRequire(path.join(ROOT, 'package.json'))('puppeteer-core');
export const FFMPEG = CFG.ffmpeg;
export const harness = (picks) => pathToFileURL(path.join(ROOT, 'live', 'test.html')).href + '#' + encodeURIComponent(picks);

export async function openFilm(picks = '{}') {
  const b = await puppeteer.launch({ executablePath: CFG.chrome, args: ['--allow-file-access-from-files', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage();
  // size the viewport from the film itself so every format renders at its own resolution
  await p.setViewport({ width: 2000, height: 2000 });
  p.on('pageerror', (e) => console.log('page error:', e.message));
  await p.goto(harness(picks), { waitUntil: 'load' });
  await p.waitForFunction('window.READY === true', { timeout: 60000 });
  const { W, H } = await p.evaluate((pk) => VID.size(JSON.parse(pk)), picks);
  await p.setViewport({ width: W, height: H });
  return { b, p, W, H };
}
