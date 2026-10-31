# 觸控按鈕截圖檢查(主 session 做)

發布 RD 不能開瀏覽器, 按鈕會不會蓋到畫面資訊只能照座標推算。流程停在 `waiting_release_pick` 時, 由你用無頭 Chrome 逐畫面截網站版的觸控模式給使用者看。檔案一律放 scratchpad, 不放進專案。

## 截圖頁(harness)

一個 html, 用 `<base href="file:///<專案>/release/game/">` 指向網站版, 照 `index.html` 的順序載入 `art/art.js` →(有的話)`audio/sound.js` → `game.js` → `touch.js`, 最後再載入你寫的「跳畫面」腳本:

- canvas 的 id 與寬高照 `index.html`, CSS 照遊戲的等比縮放寫法(例 `width: min(100vw, calc(100vh * 7 / 3)); aspect-ratio: 1680 / 720`)
- 跳畫面腳本讀網址參數(例 `?s=shop`), 直接呼叫 game.js 自己的函式造出該畫面的狀態(例: 開某座地下城、進商店、開引導卡); 先讀 game.js 找出各畫面的進入函式與要先備好的資料
- 要等計時才出現的畫面(例: 進場 3 秒後的引導): 虛擬時間下 rAF 幀很稀疏, 在跳畫面腳本裡同步呼叫 `update(1/60)` N 次推進遊戲時間, 不靠等待
- 網址帶 `&touch=1` 強制觸控模式

## 截圖

```
chrome --headless=new --user-data-dir=<暫存資料夾> --disable-gpu --hide-scrollbars --mute-audio --no-first-run
       --force-device-scale-factor=1 --allow-file-access-from-files --window-size=1680,720
       --virtual-time-budget=3000 --screenshot=<輸出.png> "file:///<harness>.html?s=<畫面>&touch=1"
```

Chrome 路徑用 `lab.renderer.find_chrome()`。每個玩家會操作的畫面都截一張(開始畫面、各選單、遊戲主畫面的左右兩端、結算、教學 / 引導卡出現時)。用 Read 看過每張, 找被按鈕蓋住的文字、數值、可選項目。

## 給使用者看與調整

- 截圖用 Artifact 發布(PNG 以 `files` 帶上, 每張標畫面名稱), 連結和選擇頁一起給使用者
- 有蓋到: 你改 `touch.js` 的 `CONFIG`(該畫面不畫那顆按鈕、或改按鈕顯示條件), 網站版與打磨版兩份同步改; 要移開遊戲資訊才改 game.js, 只在觸控模式(`PVDX.on`)下移
- 改完重截確認, 使用者看過後刪掉 Artifact
