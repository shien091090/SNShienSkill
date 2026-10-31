# 畫面寬度依裝置(發布階段)

PVD計畫網站: 電腦遊玩框 16:9, 手機橫拿全螢幕。遊戲高固定 720, 寬度在啟動時決定一次:

- 電腦: 1280(16:9)
- 觸控裝置: 照螢幕長寬比(不分直拿橫拿)與橫拿時可視區比例取大的, 夾在 1280~1680(16:9~21:9)

中間 1280×720 是**設計區**(安全區): 玩法、選單、結算都在裡面, 任何寬度都完整看得到。比 1280 寬時, 設計區置中, 兩側只放背景與貼邊的 HUD、觸控按鈕。

## 寫法

`art.js` 開頭決定寬度, 匯出 `Art.canvas.width`; `game.js`、`touch.js` 都從它讀, 不另外判斷。觸控判斷要和 `touch.js` 一致:

```js
function pickWidth() {
  var w = 1280;
  try {
    var q = /[?&]w=([0-9]+)/.exec(location.search);   // 截圖檢查用
    var mm = function (s) { return !!(window.matchMedia && matchMedia(s).matches); };
    var touch = /[?&]touch=1(&|$)/.test(location.search) || mm('(pointer: coarse)') ||
      (((navigator.maxTouchPoints || 0) > 0 || 'ontouchstart' in window) && !mm('(hover: hover)'));
    if (q) w = +q[1];
    else if (touch) {
      var a = window.screen || {}, sw = a.width || 0, sh = a.height || 0, iw = window.innerWidth || 0, ih = window.innerHeight || 0;
      var r = sw > 0 && sh > 0 ? Math.max(sw, sh) / Math.min(sw, sh) : 0;
      if (iw > ih && ih > 0) r = Math.max(r, iw / ih);
      if (r > 0) w = 720 * r;
    }
  } catch (e) { /* 取不到就用 1280 */ }
  return Math.round(Math.max(1280, Math.min(1680, w || 1280)) / 2) * 2;
}
var VW = pickWidth(), VX = -(VW - 1280) / 2;   // 畫滿整面的東西從 VX 畫到 VX+VW
try { document.documentElement.style.setProperty('--cw', String(VW)); } catch (e) { }
```

`index.html` 的畫布等比縮放照 `--cw`:

```css
canvas { display: block; width: min(100vw, calc(100vh * var(--cw, 1280) / 720)); height: auto; aspect-ratio: var(--cw, 1280) / 720; }
@supports (height: 100dvh) { canvas { width: min(100vw, calc(100dvh * var(--cw, 1280) / 720)); } }
```

`game.js`: `OX = (CW - 1280) / 2`, 每幀畫面最外層 `translate(OX, 0)` 一次, 介面座標維持 1280 設計值; 捲動鏡頭、出界判斷、邊緣提示用 `CW`。

`interface.json` 的 canvas 寫 `{"width": 1280, "height": 720, "maxWidth": 1680}`: width 是設計寬, maxWidth 是最寬(接合檢查接受兩者之間的 `Art.canvas.width`)。

## 版面要顧的

- HUD 分成左 / 中 / 右幾塊, 左右兩塊貼齊畫面邊緣(`VX + 邊距`、`VX + VW - 邊距`), 中段放在兩塊之間; 寬度不夠時中段少放大, 不讓三塊重疊。左右塊的寬度照實際字寬量, 不用固定槽位
- 手機的放大倍數跟著寬度: 1680 時可以放得比電腦大, 1280(平板)時和電腦一樣
- 檢查: 每個畫面在電腦 1280、觸控 1280 / 1560 / 1680 各截一張(`?w=寬度&touch=1`, 截圖方法見 `touch-check.md`), 看 HUD 有沒有重疊、觸控按鈕有沒有蓋住要按的東西
