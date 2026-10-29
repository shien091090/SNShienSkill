# 任務: 發布 — 網站版遊戲

這款遊戲要放上 PVD計畫網站。流程已把定版遊戲複製到 `$release_dir/game/`(網站版), 原本的遊戲在 `$src_dir/game/`。

- 遊戲名稱: $name
- 遊戲代號: $code

## 請讀取
- `$release_dir/game/` 下的 index.html、game.js、art/art.js
- `$src_dir/spec.md` 或 `$project/spec.md`(有哪份讀哪份)
- `$studio_refs/rd-lessons.md`

## 要做的事
1. **移除試玩紀錄下載**(只改 `$release_dir/game/`): 網站版不能下載任何檔案到玩家電腦。拿掉一局結束下載試玩紀錄 JSON 的函式與所有呼叫點, 以及為它存在的東西(例: 沒下載完的紀錄暫存在 `gamelog-...` localStorage 鍵、補送機制、下載按鈕)。只用來產生紀錄的事件收集可以留著不呼叫或一起拿掉, 以不留死碼、不影響玩法為準。`$src_dir/game/` 的埋點**保留**, 之後的打磨還要用
2. **名稱統一**: 開始畫面顯示的遊戲名稱若不是「$name」, 把 `$release_dir/game/` **與** `$src_dir/game/` 兩份的開始畫面名稱都改成「$name」(含 `<title>`)。名稱畫在 art.js 時可以改 art.js 裡的標題文字與為了放下新名稱必要的字級 / 位置, 不改其他圖形; 名稱太長放不下就縮字級或換行, 不改名稱
3. **介面描述**: `$release_dir/interface.json` 不存在時, 依程式實際情況寫一份給接合腳本用, 格式:
   `{"canvas": {"width": W, "height": H}, "draw": [{"name": "drawXxx", "state": ["欄位", ...]}, ...], "sounds": ["音效名", ...], "music": ["音樂名", ...]}`
   `draw` 列出 game.js 呼叫的每個 `Art.drawXxx`, 且必須含 `drawTitle`(開始畫面)與 `drawTutorial`(新手教學提示); 遊戲沒有這兩個名稱時, 在 art.js 既有的開始畫面 / 教學繪製函式上加同名別名(只加別名, 不改圖)
4. 不改其他玩法、數值、美術、音效。不改鍵名格式、不加網站溝通訊息(這次不做)
5. 用 Node vm + 假 canvas 自測兩份遊戲載入與開局不拋錯, 並確認網站版找不到任何下載(`download`、`createObjectURL`、`a.click`)的呼叫

## 回報
移除了哪些東西、名稱改在哪(兩份都要寫)、有沒有寫 interface.json、自測結果。
