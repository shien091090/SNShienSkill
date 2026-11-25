// 錄按鍵版的前置腳本 (sync.mjs 插進 game/index.html, 比遊戲本體先跑)
// 1. 遊戲邏輯用的亂數改成固定種子 (__rng), 重播時同一個種子 = 同一串亂數
// 2. performance.now 改成「遊戲步數 × 1/60 秒」: 美術動畫跟著遊戲步數走, 不跟真實時間
// 3. 遊戲迴圈改成固定 60 步/秒 (game.js 尾端由 sync.mjs 換掉), 每一次按下/放開記下發生在第幾步
// 4. 錄製時每 3 秒把紀錄送回 server.mjs 存檔 (takes/<開始時間>.json); 重播模式 (?replay) 不錄
(function () {
  var q = new URLSearchParams(location.search);
  var REPLAY = q.has('replay');
  var seed = q.has('seed') ? +q.get('seed') : Math.floor(Math.random() * 1e9);
  var s = seed >>> 0;
  window.__rng = function () {   // mulberry32
    s = (s + 0x6D2B79F5) | 0;
    var t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  var realNow = performance.now.bind(performance);
  window.__realNow = realNow;
  window.__steps = 0;
  performance.now = function () { return window.__steps * 1000 / 60; };
  window.__REPLAY = REPLAY;
  if (REPLAY) return;

  var name = new Date().toISOString().replace(/[-:]/g, '').replace('T', '-').slice(0, 15);
  var log = window.__log = { take: name, seed: seed, w: 1280, ev: [], chk: [], steps: 0 };
  window.__rec = function (type, k) { log.ev.push([window.__steps, type, k]); };
  var sent = 0;
  function send(beacon) {
    log.steps = window.__steps;
    var body = JSON.stringify(log);
    if (beacon && navigator.sendBeacon) { navigator.sendBeacon('/log', body); return; }
    fetch('/log', { method: 'POST', body: body }).then(function () { sent = log.steps; }).catch(function () { sent = -1; });
  }
  setInterval(send, 3000);
  window.addEventListener('beforeunload', function () { send(true); });

  // 右下角的錄製狀態 (在畫布外的網頁元素上, 不會進重播的畫面)
  var tag = document.createElement('div');
  tag.style.cssText = 'position:fixed;right:8px;bottom:6px;z-index:20;font:12px system-ui,"Microsoft JhengHei";color:#f66;background:rgba(0,0,0,.55);padding:2px 8px;border-radius:9px;pointer-events:none';
  document.addEventListener('DOMContentLoaded', function () { document.body.appendChild(tag); });
  setInterval(function () {
    var t = Math.floor(window.__steps / 60);
    tag.textContent = '● 錄製中 ' + name + '  ' + Math.floor(t / 60) + ':' + String(t % 60).padStart(2, '0') +
      (sent < 0 ? '  (存檔失敗: 伺服器沒開?)' : '  已存');
  }, 500);
})();
