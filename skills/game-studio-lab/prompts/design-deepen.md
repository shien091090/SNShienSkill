# 任務: 深掘階段設計(第 $round_no 輪, 產出到 `$round_dir/`)

你是遊戲設計師。深掘階段已經知道玩家要什麼體驗, 目的是**用不同的機制把目標體驗做得更強、把不要的體驗避得更乾淨**。

## 請讀取
- `$project/idea.md` — 使用者的玩法原文
- `$project/hypotheses.md` — 玩法驗證文件; 「已確認的體驗」「機制清單: 保留 / 避開」是本階段的前提
- 上一輪的回饋 `$project/$prev_round/feedback.md`
- 上一輪各款的 spec.md(`$project/$prev_round/*/spec.md`), 了解已經做過什麼
- `$studio_refs/guide-principles.md`

## 要做的事

1. 從驗證文件確認: 目標體驗(想要)、要避開的體驗(不要)、必留機制、必避機制
2. **設計 2~3 款**: 每款都包含 idea.md 的玩法與全部「保留」機制, 一律不碰「避開」機制。款與款之間的差別是**用不同的新機制去強化同一種目標體驗**(或更徹底地避開不要的體驗)
3. 新機制各寫成假設「X 機制 → 強化 Y 體驗」, 來源標「AI 發想」; 也可以重新驗證標「不確定」的舊假設
4. 更新 `$project/hypotheses.md`(用 Edit): 假設表新增(編號接續, 狀態待驗, 驗證於 $round_dir)、各款對應、修訂紀錄
5. 每款建 `$project/$round_dir/game-a/` 等資料夾, 寫 spec.md、interface.json、guide.md

### spec.md
```
# <遊戲名>(<這款的新機制>)
## 概述 / 核心循環 / 規則 / 操作(只一種輸入)/ 勝負與結束 / 數值參數表 / 物件清單 / 範圍邊界
```
只做一關、不考慮難度、不做音效。

### interface.json
`{"canvas": {...}, "draw": [{"name", "state", "size"}...], "guidePages": N}` — 物件清單每個物件一個 `draw<物件名>`, 另有 `drawBackground`(只收 ctx)與 `drawHud`; `drawGuidePage` 固定存在不列。美術與 RD 會同時照它開工, 寫完不能改。

### guide.md
照 guide-principles.md, 每頁寫文字與「圖要示意什麼」。

## 回報
每款的名稱、用了哪個新機制、驗哪幾條假設、操作方式。
