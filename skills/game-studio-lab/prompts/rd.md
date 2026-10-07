# 任務: RD($round_dir / $game)

## 請讀取
- `$game_dir/spec.md`、`$game_dir/guide.md`
- `$game_dir/interface.json` — **繪圖介面**: 美術正在同時照它畫, 你照它呼叫
- `$studio_refs/rd-lessons.md` — RD 經驗文件

## 要做的事
實作 `$game_dir/game/index.html` 與 `$game_dir/game/game.js`(可加 `style.css`)。

- `index.html` 宣告 `<meta charset="utf-8">`; 傳統 `<script src>`, 不用 module; 載入順序 `art/art.js` →(打磨階段)`audio/sound.js` → `game.js`
- 繪製一律呼叫 `Art.<函式>(ctx, state)`, 只用 interface.json 列的函式與 `Art.drawGuidePage`; state 的 key 照 interface.json
- 畫布邏輯尺寸用 interface.json 的 canvas, 依 devicePixelRatio 放大實際像素
- **美術還沒交付**: `game/art/art.js` 可能還不存在或還在改, 不要等也不要碰它。自測時在 Node vm 裡自己造一個照 interface.json 的假 Art(只在測試腳本裡, 不要寫進 game/)
- 玩家說明: 開場先顯示、可翻頁、遊戲中可再叫出。**分工**: 頁標題、說明文字(照 guide.md)、頁碼、翻頁提示由你畫; 示意圖呼叫 `Art.drawGuidePage(ctx, {page, x, y, w, h})`, `(x, y, w, h)` 是你替示意圖留的框, 必須與你畫文字的區域不重疊。美術只畫框內的圖, 不畫標題與說明文字
- 只掛 spec「操作」章節那一種輸入的監聽
- 打磨階段: 聲音一律呼叫 `Sound.play(事件)` / `Sound.playMusic(曲名)`, 事件名照 interface.json 的 sounds / music, 第一次輸入時呼叫 `Sound.init()`; 依 spec「埋點」章節逐筆記錄, 每局結束自動下載 JSON
- 開工前讀經驗文件, 收工前依它的規則回寫(先重讀再改)

## 回報
1. 做了什麼(對照 spec 章節) 2. 規格疑問(沒有就寫無) 3. 回寫了哪條經驗(沒有就寫無)
