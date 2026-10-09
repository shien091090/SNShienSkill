#!/usr/bin/env node
// 接合腳本: 用 Node vm + 假 DOM / 假 canvas 跑一款遊戲, 不開瀏覽器。
// 用法: node check.js <遊戲的 game/ 資料夾> <stage>
// 輸出最後一行: {"ok": bool, "errors": [{"step", "message"}]}
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const gameDir = path.resolve(process.argv[2] || '.');
const stage = process.argv[3] || 'explore';
const errors = [];
const fail = (step, message) => errors.push({ step, message: String(message) });
const errMsg = (e) => (e && e.stack ? e.stack.split('\n').slice(0, 3).join(' | ') : String(e));

function finish() {
  console.log(JSON.stringify({ ok: errors.length === 0, errors }));
  process.exit(0);
}

// 什麼都接受的假物件: 取任何屬性、當函式呼叫、當數字或字串用都不會拋錯
function anything() {
  const fn = function () {};
  return new Proxy(fn, {
    get(t, k) {
      if (k === Symbol.toPrimitive) return (hint) => (hint === 'string' ? '' : 0);
      if (k === 'valueOf') return () => 0;
      if (k === 'toString') return () => '';
      if (k === Symbol.iterator) return function* () {};
      if (k === 'then') return undefined;
      if (k === 'length') return 0;
      return anything();
    },
    apply() { return anything(); },
    construct() { return anything(); },
    set() { return true; },
  });
}

// 以真物件為底、缺的屬性才落到 anything()
function withFallback(base) {
  return new Proxy(base, {
    get(t, k) {
      if (k in t) return t[k];
      if (k === Symbol.toPrimitive || k === 'then') return undefined;
      return anything();
    },
  });
}

// ---- 讀介面與 index.html ----
const ifacePath = path.join(gameDir, '..', 'interface.json');
let iface;
try {
  iface = JSON.parse(fs.readFileSync(ifacePath, 'utf8'));
} catch (e) {
  fail('interface', `讀不到或無法解析 interface.json: ${e.message}`);
  finish();
}
const drawNames = (iface.draw || []).map((d) => d.name);
const guidePages = Number(iface.guidePages || 0);
// 探索 / 深掘: 說明頁(drawGuidePage 固定存在, 不列在 draw 清單);
// 打磨: 沒有說明頁, 改為開始畫面 + 嵌入式新手教學, 兩個函式必須列在 draw 清單(2026-10-09 起)
const usesGuide = stage !== 'polish';
if (!usesGuide) {
  for (const req of ['drawTitle', 'drawTutorial']) {
    if (!drawNames.includes(req)) fail('interface', `interface.json 的 draw 清單缺 ${req}(開始畫面 / 新手教學提示)`);
  }
}
const requiredDraws = usesGuide ? [...drawNames, 'drawGuidePage'] : drawNames;

const indexPath = path.join(gameDir, 'index.html');
if (!fs.existsSync(indexPath)) {
  fail('index', 'game/index.html 不存在');
  finish();
}
const html = fs.readFileSync(indexPath, 'utf8');
if (!/<meta[^>]+charset\s*=\s*["']?utf-8/i.test(html)) fail('charset', 'index.html 沒有宣告 <meta charset="utf-8">');
if (/<script[^>]+type\s*=\s*["']module["']/i.test(html)) fail('script', 'index.html 用了 type="module", file:// 下會被擋');
const scripts = [...html.matchAll(/<script[^>]*\ssrc\s*=\s*["']([^"']+)["'][^>]*>/gi)].map((m) => m[1]);
if (!scripts.some((s) => /art\/art\.js$/.test(s))) fail('script', 'index.html 沒有載入 art/art.js');
if (stage === 'polish' && !scripts.some((s) => /audio\/sound\.js$/.test(s))) fail('script', '打磨階段 index.html 沒有載入 audio/sound.js');
const artIdx = scripts.findIndex((s) => /art\/art\.js$/.test(s));
const gameIdx = scripts.findIndex((s) => /game\.js$/.test(s));
if (artIdx >= 0 && gameIdx >= 0 && artIdx > gameIdx) fail('script', 'art/art.js 必須在 game.js 之前載入');

// ---- 假瀏覽器環境 ----
let now = 0;
const rafQueue = [];
const timers = [];
let timerSeq = 1;
const listeners = []; // {target, type, fn}

function makeElement(tag) {
  const el = {
    tagName: String(tag || 'div').toUpperCase(),
    style: withFallback({}),
    width: iface.canvas?.width || 800,
    height: iface.canvas?.height || 600,
    children: [],
    dataset: {},
    classList: withFallback({ add() {}, remove() {}, toggle() {}, contains() { return false; } }),
    getContext() { return anything(); },
    getBoundingClientRect() { return { left: 0, top: 0, x: 0, y: 0, width: this.width, height: this.height, right: this.width, bottom: this.height }; },
    addEventListener(type, fn) { listeners.push({ target: proxy, type, fn }); },
    removeEventListener(type, fn) {
      const i = listeners.findIndex((l) => l.target === proxy && l.type === type && l.fn === fn);
      if (i >= 0) listeners.splice(i, 1);
    },
    appendChild(c) { this.children.push(c); return c; },
    removeChild(c) { return c; },
    setAttribute() {}, getAttribute() { return null; },
    focus() {}, blur() {}, click() {},
    querySelector() { return makeElement('div'); },
    querySelectorAll() { return []; },
  };
  const proxy = withFallback(el);
  return proxy;
}

const elements = {};
const documentObj = withFallback({
  readyState: 'complete',
  body: makeElement('body'),
  documentElement: makeElement('html'),
  getElementById(id) { return (elements[id] ||= makeElement(/canvas/i.test(id) ? 'canvas' : 'div')); },
  querySelector(sel) { return (elements[sel] ||= makeElement(/canvas/i.test(sel) ? 'canvas' : 'div')); },
  querySelectorAll() { return []; },
  createElement(tag) { return makeElement(tag); },
  addEventListener(type, fn) { listeners.push({ target: documentObj, type, fn }); },
  removeEventListener() {},
  hidden: false,
  visibilityState: 'visible',
});

const storage = new Map();
const sandbox = {
  console: { log() {}, info() {}, warn() {}, debug() {}, error() {} },
  Math, Date, JSON, Number, String, Array, Object, Boolean, Symbol, Map, Set, WeakMap, WeakSet, Promise,
  Error, TypeError, RangeError, parseInt, parseFloat, isNaN, isFinite, Infinity, NaN,
  Float32Array, Float64Array, Uint8Array, Uint8ClampedArray, Int32Array, Uint32Array, ArrayBuffer,
  document: documentObj,
  innerWidth: 1280, innerHeight: 720, devicePixelRatio: 1,
  performance: { now: () => now },
  requestAnimationFrame(cb) { rafQueue.push(cb); return rafQueue.length; },
  cancelAnimationFrame() {},
  setTimeout(cb, ms) { if (typeof cb === 'function') timers.push({ id: timerSeq, at: now + (ms || 0), cb, every: 0 }); return timerSeq++; },
  setInterval(cb, ms) { if (typeof cb === 'function') timers.push({ id: timerSeq, at: now + (ms || 16), cb, every: Math.max(ms || 16, 1) }); return timerSeq++; },
  clearTimeout(id) { const i = timers.findIndex((t) => t.id === id); if (i >= 0) timers.splice(i, 1); },
  clearInterval(id) { const i = timers.findIndex((t) => t.id === id); if (i >= 0) timers.splice(i, 1); },
  localStorage: {
    getItem: (k) => (storage.has(k) ? storage.get(k) : null),
    setItem: (k, v) => storage.set(k, String(v)),
    removeItem: (k) => storage.delete(k),
    clear: () => storage.clear(),
  },
  matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {}, addListener() {} }),
  navigator: anything(), location: anything(), screen: anything(),
  AudioContext: anything(), webkitAudioContext: anything(), Audio: anything(), Image: anything(),
  Blob: anything(), URL: anything(), fetch: anything(), XMLHttpRequest: anything(),
  alert() {}, confirm() { return false; }, prompt() { return null; },
};
sandbox.window = sandbox;
sandbox.self = sandbox;
sandbox.addEventListener = (type, fn) => listeners.push({ target: sandbox, type, fn });
sandbox.removeEventListener = () => {};
sandbox.dispatchEvent = () => true;
vm.createContext(sandbox);

function run(step, fn) {
  try { fn(); } catch (e) { fail(step, errMsg(e)); }
}

// ---- 1. 依 index.html 順序載入腳本 ----
for (const src of scripts) {
  const p = path.join(gameDir, src);
  if (!fs.existsSync(p)) { fail('load', `${src} 不存在`); continue; }
  run(`load ${src}`, () => vm.runInContext(fs.readFileSync(p, 'utf8'), sandbox, { filename: src }));
}
const inline = [...html.matchAll(/<script(?![^>]*\ssrc\s*=)[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => m[1]).filter((s) => s.trim());
inline.forEach((code, i) => run(`load inline#${i + 1}`, () => vm.runInContext(code, sandbox)));
if (errors.some((e) => e.step.startsWith('load'))) finish();

// ---- 2. Art 介面 ----
const Art = vm.runInContext('typeof Art !== "undefined" ? Art : window.Art', sandbox);
if (!Art) {
  fail('art', 'art.js 載入後沒有 window.Art');
  finish();
}
if (Art.canvas && iface.canvas && (Art.canvas.width !== iface.canvas.width || Art.canvas.height !== iface.canvas.height)) {
  fail('art', `Art.canvas ${Art.canvas.width}x${Art.canvas.height} 與介面 ${iface.canvas.width}x${iface.canvas.height} 不符`);
}
for (const name of requiredDraws) {
  if (typeof Art[name] !== 'function') { fail('art', `Art.${name} 不存在`); continue; }
  if (name === 'drawGuidePage') {
    for (let p = 0; p < Math.max(guidePages, 1); p++) {
      run('art', () => Art.drawGuidePage(anything(), withFallback({ page: p })));
    }
  } else if (name === 'drawBackground') {
    run('art', () => Art.drawBackground(anything()));
  } else {
    run('art', () => Art[name](anything(), anything()));
  }
}

// ---- 3. game.js 呼叫的 Art 函式都在介面內 ----
const allowed = new Set(requiredDraws);
for (const src of scripts.filter((s) => !/art\/|audio\//.test(s))) {
  const p = path.join(gameDir, src);
  if (!fs.existsSync(p)) continue;
  // 去掉註解再掃: 註解裡寫「Art.drawXxx」這種說明不是呼叫(GhostEchoV2 deepen-1 因此誤判一次)
  const code = fs.readFileSync(p, 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:"'`\\])\/\/.*$/gm, '$1');
  for (const m of code.matchAll(/\bArt\.(draw\w+)/g)) {
    if (!allowed.has(m[1])) fail('interface', `${src} 呼叫了介面沒有的 Art.${m[1]}`);
  }
  if (stage === 'polish') {
    const soundNames = new Set([...(iface.sounds || []), ...(iface.music || [])]);
    for (const m of code.matchAll(/\bSound\.(play|playMusic)\(\s*["'`]([\w-]+)["'`]/g)) {
      if (!soundNames.has(m[2])) fail('interface', `${src} 播放了介面沒有的音效 ${m[2]}`);
    }
  }
}

// ---- 4. 打磨: Sound ----
if (stage === 'polish') {
  const Sound = vm.runInContext('typeof Sound !== "undefined" ? Sound : window.Sound', sandbox);
  if (!Sound) fail('sound', 'sound.js 載入後沒有 window.Sound');
  else for (const fn of ['init', 'play', 'playMusic']) {
    if (typeof Sound[fn] !== 'function') fail('sound', `Sound.${fn} 不存在`);
  }
}

// ---- 5. 模擬執行 ----
function fire(types, makeEvent) {
  for (const l of listeners.filter((x) => types.includes(x.type))) {
    run(`event ${l.type}`, () => l.fn(makeEvent(l.type)));
  }
}
fire(['DOMContentLoaded', 'load'], (type) => withFallback({ type, preventDefault() {}, stopPropagation() {} }));

const canvasW = iface.canvas?.width || 800;
const canvasH = iface.canvas?.height || 600;
const keys = [' ', 'Enter', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'z', 'x'];
const codes = ['Space', 'Enter', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'KeyZ', 'KeyX'];
function inputEvent(type, i) {
  const x = ((i * 137) % canvasW) + 1;
  const y = ((i * 91) % canvasH) + 1;
  const touch = { clientX: x, clientY: y, pageX: x, pageY: y, identifier: 0 };
  return withFallback({
    type, key: keys[i % keys.length], code: codes[i % codes.length], keyCode: 32, repeat: false,
    clientX: x, clientY: y, offsetX: x, offsetY: y, pageX: x, pageY: y, button: 0, buttons: 1,
    pointerId: 1, pointerType: 'mouse', isPrimary: true, deltaY: 0,
    touches: [touch], changedTouches: [touch], targetTouches: [touch],
    target: documentObj.getElementById('canvas'), currentTarget: documentObj.getElementById('canvas'),
    preventDefault() {}, stopPropagation() {}, stopImmediatePropagation() {},
  });
}
const INPUT_SEQ = [['keydown', 'mousedown', 'pointerdown', 'touchstart'],
  ['mousemove', 'pointermove', 'touchmove'],
  ['keyup', 'mouseup', 'pointerup', 'touchend', 'click']];

let errorsBefore = errors.length;
for (let frame = 0; frame < 300; frame++) {
  now += 16;
  for (const t of timers.filter((t) => t.at <= now)) {
    run('timer', () => t.cb());
    if (t.every) t.at = now + t.every;
    else timers.splice(timers.indexOf(t), 1);
  }
  const cbs = rafQueue.splice(0);
  for (const cb of cbs) run('frame', () => cb(now));
  if (frame % 20 === 10) INPUT_SEQ.forEach((types, j) => fire(types, (type) => inputEvent(type, frame + j)));
  if (errors.length - errorsBefore > 5) { fail('frame', '錯誤過多, 提前停止模擬'); break; }
}
if (!listeners.some((l) => /key|mouse|pointer|touch|click/.test(l.type))) fail('input', '沒有註冊任何輸入事件監聽');

// 同一錯誤在每幀重複, 只留前幾筆
const seen = new Set();
const unique = errors.filter((e) => { const k = e.step + e.message; if (seen.has(k)) return false; seen.add(k); return true; });
errors.length = 0;
errors.push(...unique.slice(0, 20));
finish();
