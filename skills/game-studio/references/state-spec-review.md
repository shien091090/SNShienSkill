# 狀態: spec-review 團隊規格討論

輸入: `decisions.md`、`spec.md`、`guide.md`。兩回合討論後你判定通過或退回。企劃清單另加 guide-principles.md。

## r1 prompt

同時 spawn `game-planner`(新 session, 不是寫規格那位)與 `game-balance`。

企劃:
```
狀態: spec-review, 第 1 回合
請讀取: <game>/decisions.md、<game>/spec.md、<game>/guide.md、~/.claude/skills/game-studio/references/guide-principles.md
任務: 審這份規格: (1) 每一條定案是否都在規格裡有對應, 列出缺的 (2) 規則之間有沒有矛盾或沒定義的情況(例如兩件事同時發生怎麼判) (3) 操作是否足以支撐核心循環, 且只用一種輸入 (4) 「Demo 要驗證的問題」靠這份規格做出來的東西驗得到嗎 (5) 玩家說明: 與規格有沒有對不上、玩家會操作到的動作有沒有漏、有沒有違反 guide-principles.md(尤其是有沒有教玩家去做 Demo 要驗證的那個行為)
輸出格式: 依五點分段; 第 1、2、5 點用條列, 沒問題就寫「無」
```

數值:
```
狀態: spec-review, 第 1 回合
請讀取: <game>/decisions.md、<game>/spec.md、<game>/feedback/round-<N>-logs/ 內的全部 JSON(N = 最近一次有紀錄檔的試玩輪次; 沒有就不列)
任務: 用「數值參數表」的值推算: (1) 一局實際會多長, 與「數值方向」的目標時長差多少 (2) 有沒有參數組合會讓遊戲提前無解或無限延續 (3) 難度是否有斜率 (4) 你建議改的參數 (5) 依本版參數更新埋點欄位清單: 你這次的推算依賴哪些假設、要記哪些欄位才能校正。有試玩紀錄時, 先用它算出實測值校正你的假設, 並寫明哪些假設被實測推翻
輸出格式: 推算過程 + 建議參數表(參數 / 現值 / 建議值 / 理由) + 埋點欄位表(欄位 / 記錄時機 / 用來校正哪個假設)
```

回覆存 `discussions/spec-review-v<版號>-r1-planner.md`、`-balance.md`(版號 = round.spec-draft, 避免多次退回時檔名撞)。

## r2

照 SKILL.md 討論規則, 檔名 `discussions/spec-review-v<版號>-r2-*.md`。

## 判定

通過的條件全部要成立:
- 企劃列的「缺對應」與「矛盾」為無, 或你判斷是規格層可容忍的小洞(寫進 log)
- 數值推算的時長與目標差距在你可接受範圍, 且沒有無解/無限的組合
- 你自己讀一遍: RD 拿到這份能不能開工不用猜
- 執行守則中標記 spec-review 的條目; 企劃第 5 點若只是說明的文字問題, 你直接改 guide.md 並註記進通過那行 log, 不必退回; 數值第 5 點的埋點欄位異動只改埋點、不動規則時, 你直接改 spec.md 的「埋點」章節與 decisions.md「埋點」段, 同樣註記進 log, 不構成退回

任一不成立 → 退回。

## 退回程序

N = round.spec-draft, M = decisions.md 修訂紀錄最後一條的版號。

1. 先照 SKILL.md 轉移程序把 `spec.md` 搬 `archive/spec.v<N>.md`、`guide.md` 搬 `archive/guide.v<N>.md`, `decisions.md` 搬 `archive/decisions.v<M>.md`
2. 改 `decisions.md`: 只改被這次討論推翻或補充的段落; 數值 agent 建議採納的參數寫進「數值方向」; 修訂紀錄加一條 `- v<M+1> <日期> 觸發: spec-review 第 N 版退回; 改了: ...; 原因: ...`
3. STATE.md → `spec-draft`, round.spec-draft +1, log 寫退回理由
4. 回報使用者: 退回原因一到兩條、決策改了什麼

## 通過程序

照 SKILL.md 轉移程序 → `build`, 不搬 archive、版號不變。log 寫一行:「spec v<round.spec-draft> 通過, 進 build 完整實作; 容忍小洞: …(若有); 參數調整: …(若有)」。數值建議的小幅參數調整(單一參數、不改規則)由你直接改 spec.md, 註記併入這行 log, 不另起新行; 涉及規則或多個參數連動一律退回。回報使用者: 通過、調了什麼(若有)。
