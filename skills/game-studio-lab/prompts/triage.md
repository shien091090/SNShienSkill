# 任務: 錯誤判定($round_dir / $game)

接合腳本(Node vm + 假 canvas 實際載入遊戲)檢查沒過。你的工作是**判斷該退回給誰、怎麼改**, 不是自己修。

## 請讀取
- 接合腳本的報告 `$report`
- `$game_dir/interface.json` — 美術與 RD 共同遵守的繪圖介面, 這是判定對錯的依據
- `$game_dir/game/` 下全部程式: index.html、game.js、art/art.js(、audio/sound.js)

## 判定原則
- `Art.drawGuidePage(ctx, state)` 是介面固定的一部分(畫說明頁), 不列在 interface.json 的 draw 清單裡, 但 game.js 呼叫它是**合法的**, 不要當成越界
- 誰沒照 interface.json 做, 就退給誰。例: Art 少了介面上的函式 → art; game.js 呼叫介面外的函式或傳錯欄位 → rd; Sound 少了事件 → audio
- 錯誤發生在某方的程式裡, 但根因是另一方沒照介面 → 退給根因那方
- 雙方都有問題 → 兩方都退, 各寫各的修改方向
- 可選的退回對象: $roles

## 輸出
**只寫一個檔** `$out`, 內容為 JSON:
```json
{ "targets": { "rd": "具體修改方向: 哪個檔、哪裡、改成什麼" }, "reason": "判定理由一兩句" }
```
`targets` 的 key 只能是 $roles 之一, 至少一個。不要改任何其他檔。
