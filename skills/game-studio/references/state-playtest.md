# 狀態: playtest 試玩回饋

續接: feedback/round-<round.playtest>.md 已有內容 → 從既有條目接著收, 不重建。

使用者玩, 你收。每則回饋先分類再處理, 邊收邊寫 `feedback/round-<round.playtest>.md`。

## 分類

先執行守則中標記 playtest 的條目(R2: 說明與遊戲實際行為不符算 bug), 再照下表分類。

| 類型 | 判準 | 處理 |
|---|---|---|
| bug | 行為與 spec.md 不符, 或報錯、卡死、開不了 | 立刻交 RD, 不等 |
| 美術 | 看不清、分不出、不好看、尺寸怪, 但行為對 | 記下, 等本輪講完 |
| 玩法 | 規則、節奏、難度、操作感、「不好玩」 | 記下, 等本輪講完 |

分不清 bug 還是玩法 → 對 spec.md: spec 有寫而沒做到是 bug; spec 寫了但玩起來不對是玩法。你判, 不問使用者。

## bug 處理

一批處理: 使用者一次講的 bug 你整理成一份描述(每條: 現象 / 重現步驟 / 對應 spec 條目), 然後 spawn `game-rd`(新 session):

```
狀態: playtest, 修 bug
請讀取: ~/.claude/skills/game-studio/references/rd-lessons.md、<game>/spec.md, 以及 <game>/game/ 下的檔案(這裡刻意給整個目錄, 因為修 bug 要看全部程式)
任務: 修下列 bug, 每條先重現(讀碼定位)再修, 修完 node --check 並逐條自查:
<bug 清單>
不改 spec.md、不改 game/art/。收工前依經驗文件規則回寫。
輸出格式: 逐條 bug 說明原因與修法; 經驗文件回寫了哪條 / 無
```

修完你讀 RD 回報與 diff 確認每條 bug 都有對應修法, 在 feedback 檔 bug 條目打勾, 請使用者繼續玩。不轉移。

## 美術與玩法回饋

使用者講到美術或玩法時, 記進 feedback 檔對應段。**在他繼續講的時候不動作**。你判斷他這輪告一段落(例如說「大概就這些」或停下來問你), 問一句:「這一輪回饋給完了嗎? 還是還有要補的?」這是本狀態唯一會問使用者的問題。

他說給完了 →
- **只有美術回饋**: feedback「製作人處理」寫「美術: 留待 build 交美術」→ 照 SKILL.md 轉移程序 → `build`(美術修正路徑), log 最後一行寫「playtest 第 <round.playtest> 輪美術回饋, 進 build 美術修正」
- **有玩法回饋(不論有沒有美術)**: M = decisions.md 修訂紀錄最後一條的版號
  1. 先照轉移程序把 `decisions.md` 搬 `archive/decisions.v<M>.md`、`spec.md` 搬 `archive/spec.v<round.spec-draft>.md`、`guide.md`(存在才搬)搬 `archive/guide.v<round.spec-draft>.md`
  2. 改 `decisions.md`: 你把玩法回饋轉成設計決策(使用者說「太難」, 你決定是調參數方向還是改規則, 寫進對應段); 修訂紀錄加 `- v<M+1> <日期> 觸發: playtest 第 <round.playtest> 輪玩法回饋; 改了: ...; 原因: ...`
  3. feedback「製作人處理」寫: 玩法併入 decisions v<M+1>; 美術留待下次 build
  4. STATE.md → `spec-draft`, round.spec-draft +1, log
  5. 回報使用者: 你把他的回饋轉成了什麼決策, 接下來規格會重擬

美術回饋留在 feedback 檔, 下次走到 build 完整實作時, 美術的檔案清單多帶這份 feedback(見 state-build.md)。

## 結束

使用者說「可以了」「夠了」「先到這」→ STATE.md → `done`, log 一行。回報: 總共幾版規格、幾輪試玩、最後驗證問題的答案是什麼(你的判斷, 一句)。
