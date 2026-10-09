# 任務: RD($round_dir / $game)

## 請讀取
- `$game_dir/spec.md`、`$game_dir/guide.md`(探索 / 深掘才有)
- `$game_dir/interface.json` — **繪圖介面**: 美術正在同時照它畫, 你照它呼叫
- `$studio_refs/rd-lessons.md` — RD 經驗文件

## 要做的事
實作 `$game_dir/game/index.html` 與 `$game_dir/game/game.js`(可加 `style.css`)。

- **打磨的後續輪次**: `game/game.js` 已經存在時, 照 spec.md 的「本輪改動」在既有程式上修改, 不要整份重寫(上一輪修過的 bug 與手感會流失)

- `index.html` 宣告 `<meta charset="utf-8">`; 傳統 `<script src>`, 不用 module; 載入順序 `art/art.js` →(打磨階段)`audio/sound.js` → `game.js`
- 繪製一律呼叫 `Art.<函式>(ctx, state)`, 只用 interface.json 列的函式(探索 / 深掘另加 `Art.drawGuidePage`); state 的 key 照 interface.json
- 畫布邏輯尺寸用 interface.json 的 canvas, 依 devicePixelRatio 放大實際像素
- **美術還沒交付**: `game/art/art.js` 可能還不存在或還在改, 不要等也不要碰它。自測時在 Node vm 裡自己造一個照 interface.json 的假 Art(只在測試腳本裡, 不要寫進 game/)
- **探索 / 深掘的玩家說明(說明頁)**: 開場先顯示、可**前後**翻頁(要能回上一頁, 玩家漏看才回得去)、遊戲中可再叫出。**分工**: 頁標題、說明文字(照 guide.md)、頁碼、翻頁提示由你畫; 示意圖呼叫 `Art.drawGuidePage(ctx, {page, x, y, w, h})`, `(x, y, w, h)` 是你替示意圖留的框, 必須與你畫文字的區域不重疊。美術只畫框內的圖, 不畫標題與說明文字
- **打磨的玩家說明(開始畫面 + 嵌入式新手教學, 沒有說明頁)**: 開場是開始畫面(`Art.drawTitle`), 玩家用 spec 指定的輸入開始後直接進遊戲。照 spec「新手教學」表實作教學狀態: 每個階段在「出現時機」到了才出現, 玩家達成「完成條件」就播完成特效、進下一階段; 已完成的階段不再出現, 整關重來(R)與失敗重來都不重置。教學提示一律呼叫 `Art.drawTutorial(ctx, state)` 傳 state(階段、文字、按鍵、已按過哪些鍵、完成特效進度、位置), **你不自己畫教學文字或按鍵圖示**。上一版有說明頁就整個拿掉。教學的每個階段都要記進埋點(出現、完成), 才看得出新手卡在哪一步
- 只掛 spec「操作」章節那一種輸入的監聽
- 打磨階段: 聲音一律呼叫 `Sound.play(事件)` / `Sound.playMusic(曲名)`, 事件名照 interface.json 的 sounds / music, 第一次輸入時呼叫 `Sound.init()`; 依 spec「埋點」章節逐筆記錄, 每局結束自動下載 JSON
- 開工前讀經驗文件, 收工前依它的規則判斷要不要寫經驗提案到收件匣(見共同守則)

## 回報
1. 做了什麼(對照 spec 章節) 2. 規格疑問(沒有就寫無) 3. 寫了哪條經驗提案(沒有就寫無)
