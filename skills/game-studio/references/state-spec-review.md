# 狀態: spec-review 團隊規格討論

輸入: `decisions.md`、`spec.md`、`telemetry.md`、`guide.md`。兩回合討論後你判定通過、就地修正或退回。企劃清單另加 guide-principles.md。

## r1 prompt

同時 spawn `game-planner`(新 session, 不是寫規格那位)與 `game-balance`。

企劃:
```
狀態: spec-review, 第 1 回合
請讀取: <game>/decisions.md、<game>/spec.md、<game>/telemetry.md、<game>/guide.md、~/.claude/skills/game-studio/references/guide-principles.md
任務: 審這份規格: (1) 每一條定案是否都在規格裡有對應, 列出缺的 (2) 規則之間有沒有矛盾或沒定義的情況(例如兩件事同時發生怎麼判) (3) 操作是否足以支撐核心循環, 且只用一種輸入 (4) 「Demo 要驗證的問題」靠這份規格做出來的東西驗得到嗎 (5) 玩家說明: 與規格有沒有對不上、玩家會操作到的動作有沒有漏、有沒有違反 guide-principles.md(尤其是有沒有教玩家去做 Demo 要驗證的那個行為)
輸出格式: 依五點分段; 第 1、2、5 點用條列, 沒問題就寫「無」
```

數值:
```
狀態: spec-review, 第 1 回合
請讀取: <game>/decisions.md、<game>/spec.md、<game>/telemetry.md、<game>/feedback/round-<N>-logs/ 內的全部 JSON(N = 最近一次有紀錄檔的試玩輪次; 沒有就不列)
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
- 執行守則中標記 spec-review 的條目; 企劃第 5 點若只是說明的文字問題, 你直接改 guide.md 並註記進通過那行 log, 不必退回; 數值第 5 點的埋點欄位異動只改埋點、不動規則時, 你直接改 telemetry.md 與 decisions.md「埋點」段, 同樣註記進 log, 不構成退回

任一不成立 → 先看能不能就地修正, 不能才退回。

## 就地修正(優先於退回)

r2 之後, 要改的東西若同時符合下列條件, 不退回、不重寫, 改為就地修:
- 不改「Demo 要驗證的問題」與「核心循環」
- 每一處修法都已具體到可以直接寫進規格(數值給了確切參數值、企劃或數值給了 RD 可直接實作的規則文字), 或是兩方給了明確選項、你選一邊即可
- 不是整章重寫(要改的規則條目約在全部規則的三分之一以內; 超過就退回)

多參數連動、新增一條規則, 只要符合上面三條都可以就地修。

程序:
1. `decisions.md` 搬 `archive/decisions.v<M>.md`, 改 decisions.md: 寫入你的裁決與採納的參數, 修訂紀錄加 `- v<M+1> <日期> 觸發: spec-review 第 N 版就地修正; 改了: ...; 原因: ...`。spec 版號不變, 不搬 spec / telemetry / guide
2. SendMessage 給本回合的**企劃**(r1 / r2 那位, 已讀過全文), 給逐條修正清單(每條: 改哪個檔哪一段 / 改成什麼), 任務「照清單修改 spec.md、telemetry.md、guide.md, 清單外不動; 回報逐條改了哪裡」。企劃 session 失效就重 spawn, 清單給 decisions.md、spec.md、telemetry.md、guide.md。**game-planner 只有 Write、沒有 Edit**, spec / telemetry 動輒數萬 token, 整份覆寫會被截斷寫壞: 任務改成「小檔(guide.md)直接改; 大檔逐條給『找原句 → 換成』清單, 原句須對過原文」, 你把清單存成 scratchpad 檔, 再 spawn general-purpose(sonnet)照清單用 Edit 套用並 Grep 自查, 你再核 diff
3. 你讀 diff 逐條核對, 再做一次上面「通過的條件」自讀(RD 能不能開工不用猜)。核對不過 → SendMessage 同一個企劃補
4. 走下面「通過程序」, log 那行寫「spec v<N> 就地修正後通過, 進 build 完整實作; 就地修正: …; 容忍小洞: …」

不再另跑一輪審查討論。

## 退回程序

N = round.spec-draft, M = decisions.md 修訂紀錄最後一條的版號。

1. 先照 SKILL.md 轉移程序把 `spec.md` 搬 `archive/spec.v<N>.md`、`telemetry.md` 搬 `archive/telemetry.v<N>.md`(存在才搬)、`guide.md` 搬 `archive/guide.v<N>.md`, `decisions.md` 搬 `archive/decisions.v<M>.md`
2. 改 `decisions.md`: 只改被這次討論推翻或補充的段落; 數值 agent 建議採納的參數寫進「數值方向」; 修訂紀錄加一條 `- v<M+1> <日期> 觸發: spec-review 第 N 版退回; 改了: ...; 原因: ...`
3. STATE.md → `spec-draft`, round.spec-draft +1, log 寫退回理由
4. 回報使用者: 退回原因一到兩條、決策改了什麼

## 通過程序

照 SKILL.md 轉移程序 → `build`, 不搬 archive、版號不變。log 寫一行:「spec v<round.spec-draft> 通過, 進 build 完整實作; 容忍小洞: …(若有); 參數調整: …(若有)」。數值建議的小幅參數調整(單一參數、不改規則)由你直接改 spec.md, 註記併入這行 log, 不另起新行; 涉及規則或多個參數連動走上面的就地修正。回報使用者: 通過、調了什麼(若有)。
