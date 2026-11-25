// node tools/pagecheck.mjs — load the review page headless, report JS errors, screenshot to renders/page.png
import puppeteer from 'puppeteer-core';
import fs from 'fs'; import path from 'path'; import { pathToFileURL } from 'url';
const cfg = JSON.parse(fs.readFileSync('video.config.json'));
const b = await puppeteer.launch({ executablePath: cfg.chrome, args: ['--allow-file-access-from-files'] });
const p = await b.newPage(); await p.setViewport({ width: 1400, height: 900 });
const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => m.type() === 'error' && errs.push(m.text()));
await p.goto(pathToFileURL(path.resolve('live/index.html')).href, { waitUntil: 'load' });
await new Promise(r => setTimeout(r, 6000));
await p.screenshot({ path: 'renders/page.png' });
console.log('errors:', errs.slice(0, 5));
await b.close();
