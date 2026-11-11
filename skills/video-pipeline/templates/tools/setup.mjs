// node tools/setup.mjs — one-time setup of a video folder (re-runnable; skips what already exists).
// Installs puppeteer-core + a headless Chrome into the folder, a Python venv with the audio libraries and
// ffmpeg (imageio-ffmpeg), and writes video.config.json with the resolved paths.
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const run = (cmd) => execSync(cmd, { cwd: ROOT, stdio: ['ignore', 'pipe', 'inherit'] }).toString().trim();
const win = process.platform === 'win32';

// prerequisites: stop with one readable line instead of a stack trace
const has = (cmd) => { try { execSync(cmd, { stdio: 'ignore' }); return true; } catch { return false; } };
const PY = win ? 'py -3' : 'python3';
const missing = [['npm --version', 'npm(隨 Node.js 安裝: https://nodejs.org)'], [`${PY} --version`, 'Python 3(https://www.python.org, Windows 要勾選 py launcher)']]
  .filter(([cmd]) => !has(cmd)).map(([, name]) => name);
if (missing.length) { console.error('缺少: ' + missing.join('、') + '。裝好後重跑 node tools/setup.mjs'); process.exit(2); }

if (!fs.existsSync(path.join(ROOT, 'package.json'))) fs.writeFileSync(path.join(ROOT, 'package.json'), JSON.stringify({ private: true, type: 'module' }, null, 1));
if (!fs.existsSync(path.join(ROOT, 'node_modules', 'puppeteer-core'))) { console.log('installing puppeteer-core ...'); run('npm i puppeteer-core@23.11.1 @puppeteer/browsers@2.6.1 --no-audit --no-fund'); }

console.log('installing chrome-headless-shell ...');
const line = run(`npx --no-install @puppeteer/browsers install chrome-headless-shell@stable --path "${path.join(ROOT, '.cache')}"`).split('\n').pop();
const chrome = line.slice(line.indexOf(' ') + 1).trim(); // "chrome-headless-shell@<ver> <path>"

const venvPy = path.join(ROOT, '.venv', win ? 'Scripts/python.exe' : 'bin/python');
if (!fs.existsSync(venvPy)) { console.log('creating .venv ...'); run(`${PY} -m venv .venv`); }
console.log('installing audio libraries ...');
run(`"${venvPy}" -m pip install -q imageio-ffmpeg numpy scipy soundfile pyloudnorm librosa`);
const ffmpeg = run(`"${venvPy}" -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"`);

const cfg = { chrome, ffmpeg, python: venvPy };
fs.writeFileSync(path.join(ROOT, 'video.config.json'), JSON.stringify(cfg, null, 1));
console.log(cfg);
