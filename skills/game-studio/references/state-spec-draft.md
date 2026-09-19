# 狀態: spec-draft 企劃擬定 Demo 規格

輸入: `decisions.md`; 若 `round.spec-draft > 1`, 加上 `archive/spec.v<N-1>.md`。輸出: `spec.md`。只 spawn 企劃, 不討論。

## prompt

spawn `game-planner`(新 session)。

第一版(round.spec-draft == 1):
```
狀態: spec-draft, 規格第 1 版
請讀取: <game>/decisions.md
任務: 依定案結果寫 Demo 玩法規格, 存到 <game>/spec.md。只寫玩法, 不寫美術表現、不寫音效、不寫技術實作。「數值參數表」以定案的數值方向為底給出具體初始值, 並包含畫面寬與畫面高。「物件清單」列出所有會出現在畫面上、玩家需要辨識的東西與它們的狀態。「Demo 範圍邊界」把定案的「明確不做的」抄進來並補上你認為 Demo 不該碰的。
輸出格式: 章節照下列模板, 不增刪:
<貼 templates.md 的 spec.md 區塊, 標題 v1>
寫完回報: 待定項目有幾個、各是什麼原因
```

退回重寫(round.spec-draft > 1):
```
狀態: spec-draft, 規格第 <N> 版
請讀取: <game>/decisions.md、<game>/archive/spec.v<N-1>.md
任務: decisions.md 已修訂, 重點看「修訂紀錄」最後一條, 那是這次改版的原因。以上一版規格為底改出第 <N> 版存到 <game>/spec.md, 沒被修訂影響的章節維持原樣, 不要無故重寫。
輸出格式: 章節照模板(同上, 標題 v<N>)。寫完回報: 改了哪些章節、對應修訂紀錄的哪一點
```

## 你的檢查(不討論, 只把關格式)

- 章節齊全、「物件清單」沒寫外觀、「待定」不是空的就是有原因、「數值參數表」有畫面尺寸
- 格式不對 → SendMessage 同一個 agent 要他修, 不重 spawn
- 內容好壞不在這裡判, 那是 spec-review 的事

## 轉移

照 SKILL.md 轉移程序 → `spec-review`。回報使用者: 規格第 N 版落地、待定幾項。
