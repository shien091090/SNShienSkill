# 觸控按鈕截圖檢查(主 session 做)

發布 RD 不能開瀏覽器, 按鈕會不會蓋到畫面資訊只能照座標推算。流程停在 `waiting_release_pick` 時, 由你用無頭 Chrome 逐畫面截網站版的觸控模式給使用者看。檔案一律放 scratchpad, 不放進專案。

## 截圖頁(harness)

一個 html, 用 `<base href="file:///<專案>/release/game/">` 指向網站版, 照 `index.html` 的順序載入 `art/art.js` →(有的話)`audio/sound.js` → `game.js` → `touch.js`, 最後再載入你寫的「跳畫面」腳本:

- canvas 的 id 與寬高照 `index.html`, CSS 照遊戲的等比縮放寫法(例 `width: min(100vw, calc(100vh * var(--cw, 1280) / 720)); aspect-ratio: var(--cw, 1280) / 720`)
- 跳畫面腳本讀網址參數(例 `?s=shop`), 直接呼叫 game.js 自己的函式造出該畫面的狀態(例: 開某座地下城、進商店、開引導卡); 先讀 game.js 找出各畫面的進入函式與要先備好的資料
- 要等計時才出現的畫面(例: 進場 3 秒後的引導): 虛擬時間下 rAF 幀很稀疏, 在跳畫面腳本裡同步呼叫 `update(1/60)` N 次推進遊戲時間, 不靠等待
- 網址帶 `&touch=1` 強制觸控模式, `&w=<寬>` 指定畫面寬度(無頭 Chrome 的螢幕尺寸不等於視窗, 不指定會判成 1280)
- 寬度依裝置的遊戲, 每個畫面截電腦 1280(不帶 touch)、觸控 1280 / 1560 / 1680 四種, `--window-size` 跟著寬度

## 截圖

```
chrome --headless=new --user-data-dir=<暫存資料夾> --disable-gpu --hide-scrollbars --mute-audio --no-first-run
       --force-device-scale-factor=1 --allow-file-access-from-files --window-size=<寬>,720
       --timeout=2500 --screenshot=<輸出.png> "file:///<harness>.html?s=<畫面>&touch=1"
```

- 用 `--timeout`, 不用 `--virtual-time-budget`: 遊戲的 rAF 迴圈一直排新的一幀, 虛擬時間永遠等不到閒置, Chrome 會卡死不出圖。跳畫面腳本造好畫面後, 把遊戲的每幀更新換成空函式(畫面凍結在那一刻, 只剩繪製), 截到的才是造出來的狀態
- 每次截圖外面包 `timeout 40`。卡死殘留的 headless Chrome 會鎖住 `--user-data-dir`, 之後每次截圖都秒退、不出檔: 截圖秒退時先結束殘留的 chrome 行程或換一個新的暫存資料夾

Chrome 路徑用 `lab.renderer.find_chrome()`。每個玩家會操作的畫面都截一張(開始畫面、各選單、遊戲主畫面的左右兩端、結算、教學 / 引導卡出現時)。用 Read 看過每張, 找被按鈕蓋住的文字、數值、可選項目; 確認兩側是純黑塊(沒有延伸出來的背景、壓暗、HUD); 也確認畫面寫到的每個鍵(鍵帽與純文字的「按 Z」「空白鍵」, 含介面列的操作提示)在手機上都有按鈕, 沒有的不該出現(例: Esc 暫停、M 靜音、C 開圖鑑), 以及畫面要求按的鍵(例: 引導卡的「A 繼續」)真的有畫出來——疊在不能操作的場景上的引導最容易漏(例: 見習表演的引導卡, 表演場整組不畫, 卡片要按 A 卻沒有 A 鈕)。

## 給使用者看與調整

- 截圖用 Artifact 發布(PNG 以 `files` 帶上, 每張標畫面名稱), 連結和選擇頁一起給使用者
- 有蓋到: 你改 `touch.js` 的 `CONFIG`(該畫面不畫那顆按鈕、或改按鈕顯示條件), 網站版與打磨版兩份同步改; 要移開遊戲資訊才改 game.js, 只在觸控模式(`PVDX.on`)下移。黑塊不夠寬時按鈕壓到設計區邊緣一點是刻意的取捨(不縮小遊戲畫面, 免得 HUD 字太小), 只處理蓋住要按的東西或關鍵資訊的情況
- 按鍵提示對不上(上一點檢查到的): 改 game.js / art.js 讓那段提示在 `PVDX.on` 時換字或不畫, 一樣兩份同步; 手機缺的常用功能(例: 開圖鑑)接到 `touch.js` 的功能鍵 d
- 改完重截確認, 使用者看過後刪掉 Artifact
