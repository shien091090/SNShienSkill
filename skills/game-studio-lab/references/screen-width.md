# 畫面寬度依裝置(發布階段)

PVD計畫網站: 電腦遊玩框 16:9, 手機橫拿全螢幕。遊戲高固定 720, 寬度在啟動時決定一次:

- 電腦: 1280(16:9)
- 觸控裝置: 橫拿時照實際可視區(網站遊戲框)的長寬比, 直拿時照螢幕長寬比, 夾在 1280~1680(16:9~21:9); 不取兩者較大值, 否則可視區比螢幕窄時上下會留邊

中間 1280×720 是**設計區**: 遊戲的一切(玩法、HUD、選單、結算、背景)都在裡面。只有觸控裝置會比 1280 寬, 這時設計區置中、上下貼邊、不縮小(縮小後 HUD 字太小看不清), 兩側多出來的寬度由 `touch.js` 塗成黑塊、放觸控按鈕; 遊戲不往兩側延伸背景、壓暗或 HUD。黑塊不夠寬時(一般手機、1280 寬平板)按鈕會壓到設計區邊緣一點, 這是刻意的取捨。

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
      if (iw > ih && ih > 0) r = iw / ih;   // 橫拿時以實際可視區為準(網站框會扣掉瀏海安全區, 比整個螢幕窄; 取螢幕比例會上下留邊)
      if (r > 0) w = 720 * r;
    }
  } catch (e) { /* 取不到就用 1280 */ }
  return Math.round(Math.max(1280, Math.min(1680, w || 1280)) / 2) * 2;
}
var VW = pickWidth(), VX = -(VW - 1280) / 2;   // VX: 一側黑塊寬的負值(設計座標); 遊戲本身不畫到 VX 外
try { document.documentElement.style.setProperty('--cw', String(VW)); } catch (e) { }
```

`index.html` 的畫布等比縮放照 `--cw`:

```css
canvas { display: block; width: min(100vw, calc(100vh * var(--cw, 1280) / 720)); height: auto; aspect-ratio: var(--cw, 1280) / 720; }
@supports (height: 100dvh) { canvas { width: min(100vw, calc(100dvh * var(--cw, 1280) / 720)); } }
```

`game.js`: `OX = (CW - 1280) / 2`, 每幀畫面最外層 `translate(OX, 0)` 一次, 介面座標維持 1280 設計值; 捲動鏡頭、出界判斷、邊緣提示也維持設計區寬 1280。

`interface.json` 的 canvas 寫 `{"width": 1280, "height": 720, "maxWidth": 1680}`: width 是設計寬, maxWidth 是最寬(接合檢查接受兩者之間的 `Art.canvas.width`)。

## 版面要顧的

- HUD、背景、壓暗都只畫在設計區 0~1280 內, 不畫到設計區外(觸控時兩側會被黑塊蓋掉)
- 觸控模式下, 畫面上提到的按鍵都要有對應的觸控按鈕或拿掉: 手機沒有的通用鍵(暫停 Esc、靜音 M、其他功能鍵)的提示在 `PVDX.on` 時不畫; 常用功能鍵(例: 開圖鑑)交給 `touch.js` 的功能鍵 d, 畫在設計區右上角(電腦版聲音開關圖示的位置, 觸控模式不畫聲音圖示所以空著)
- 手機字級下限(觸控模式才套用, 電腦版不動): 手機橫拿時設計區約 390 CSS px 高, 照電腦版的字級下限(art-lessons「字太小」那條, 畫布高約 1/77)畫的字在手機只剩 5~9px。觸控模式(`PVDX.on`)下, 玩家要讀的字至少畫布高的 1/35(實際約 11px; 720 高約 21px), 要辨識的小圖示(單位頭上的狀態 / 部件圖示、鍵帽、格子裡的圖示)至少 1/24(實際約 16px; 720 高 30px)。畫布高以遊戲畫圖時用的座標高度算: 用較小座標畫再整體放大的遊戲(例: 用 1024×576 畫、放大成 1280×720), 照 576 算, 字約 17px、圖示約 24px。集中在文字繪製函式把小於下限的字級拉上來, 再逐一修放大後擠到、疊到或被觸控按鈕蓋住的版面(一樣只在觸控模式); 純裝飾不用讀的字可以不放大
- 檢查: 每個畫面在電腦 1280、觸控 1280 / 1560 / 1680 各截一張(`?w=寬度&touch=1`, 截圖方法見 `touch-check.md`), 看 HUD 有沒有重疊、觸控按鈕有沒有蓋住要按的東西
