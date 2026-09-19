# 狀態: spec-review 團隊規格討論

輸入: `decisions.md`、`spec.md`。兩回合討論後你判定通過或退回。

## r1 prompt

同時 spawn `game-planner`(新 session, 不是寫規格那位)與 `game-balance`。

企劃:
```
狀態: spec-review, 第 1 回合
請讀取: <game>/decisions.md、<game>/spec.md
任務: 審這份規格: (1) 每一條定案是否都在規格裡有對應, 列出缺的 (2) 規則之間有沒有矛盾或沒定義的情況(例如兩件事同時發生怎麼判) (3) 操作是否足以支撐核心循環 (4) 「Demo 要驗證的問題」靠這份規格做出來的東西驗得到嗎
輸出格式: 依四點分段; 第 1、2 點用條列, 沒問題就寫「無」
```

數值:
```
狀態: spec-review, 第 1 回合
請讀取: <game>/decisions.md、<game>/spec.md
任務: 用「數值參數表」的值推算: (1) 一局實際會多長, 與「數值方向」的目標時長差多少 (2) 有沒有參數組合會讓遊戲提前無解或無限延續 (3) 難度是否有斜率 (4) 你建議改的參數
輸出格式: 推算過程 + 建議參數表(參數 / 現值 / 建議值 / 理由)
```

回覆存 `discussions/spec-review-v<版號>-r1-planner.md`、`-balance.md`(版號 = round.spec-draft, 避免多次退回時檔名撞)。

## r2

照 SKILL.md 討論規則, 檔名 `discussions/spec-review-v<版號>-r2-*.md`。

## 判定

通過的條件全部要成立:
- 企劃列的「缺對應」與「矛盾」為無, 或你判斷是規格層可容忍的小洞(寫進 log)
- 數值推算的時長與目標差距在你可接受範圍, 且沒有無解/無限的組合
- 你自己讀一遍: RD 拿到這份能不能開工不用猜

任一不成立 → 退回。

## 退回程序

N = round.spec-draft, M = decisions.md 修訂紀錄最後一條的版號。

1. 先照 SKILL.md 轉移程序把 `spec.md` 搬 `archive/spec.v<N>.md`, `decisions.md` 搬 `archive/decisions.v<M>.md`
2. 改 `decisions.md`: 只改被這次討論推翻或補充的段落; 數值 agent 建議採納的參數寫進「數值方向」; 修訂紀錄加一條 `- v<M+1> <日期> 觸發: spec-review 第 N 版退回; 改了: ...; 原因: ...`
3. STATE.md → `spec-draft`, round.spec-draft +1, log 寫退回理由
4. 回報使用者: 退回原因一到兩條、決策改了什麼

## 通過程序

照 SKILL.md 轉移程序 → `build`, 不搬 archive、版號不變。log 寫一行:「spec v<round.spec-draft> 通過, 進 build 完整實作; 容忍小洞: …(若有); 參數調整: …(若有)」。數值建議的小幅參數調整(單一參數、不改規則)由你直接改 spec.md, 註記併入這行 log, 不另起新行; 涉及規則或多個參數連動一律退回。回報使用者: 通過、調了什麼(若有)。
