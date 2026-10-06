# 狀態: spec-draft 企劃擬定 Demo 規格

輸入: `decisions.md`、`guide-principles.md`; 若 `round.spec-draft > 1`, 加上 `archive/spec.v<N-1>.md` 與 `archive/guide.v<N-1>.md`(存在才給)。輸出: `spec.md`、`telemetry.md`、`guide.md`。只 spawn 企劃, 不討論。

續接: spec.md、telemetry.md、guide.md 都已存在且比 decisions.md 新 → 企劃已交稿, 直接做你的檢查; 缺 telemetry.md 或 guide.md → SendMessage 同一個 agent 補(session 已失效就重 spawn, 清單給 decisions.md、spec.md、guide-principles.md)。

## prompt

spawn `game-planner`(新 session)。

第一版(round.spec-draft == 1):
```
狀態: spec-draft, 規格第 1 版
請讀取: <game>/decisions.md、~/.claude/skills/game-studio/references/guide-principles.md
任務: 依定案結果寫 Demo 玩法規格, 存到 <game>/spec.md。「操作」章節只列 decisions.md 選定的那一種輸入, 每個玩家動作都要有對應。埋點欄位照 decisions.md「埋點」段寫進 <game>/telemetry.md(章節照 templates.md 的 telemetry.md 模板), 不自己增刪欄位; spec.md 的「埋點」章節只留一行指向 telemetry.md。spec.md 只寫現行規則, 不寫版本沿革與設計理由(理由在 decisions.md)。只寫玩法, 不寫美術表現、不寫技術實作; 聲音只寫在「音效清單」章節(哪些事件要有聲音、要讓玩家感覺到什麼、背景音樂幾首、靜音怎麼操作), 不寫素材與做法, decisions.md 沒要音效就寫無。「數值參數表」以定案的數值方向為底給出具體初始值, 並包含畫面寬與畫面高。「物件清單」列出所有會出現在畫面上、玩家需要辨識的東西與它們的狀態。「Demo 範圍邊界」把定案的「明確不做的」抄進來並補上你認為 Demo 不該碰的。
輸出格式: 章節照下列模板, 不增刪:
<貼 templates.md 的 spec.md 區塊, 標題 v1>
規格寫完後, 依 guide-principles.md 另寫給玩家看的遊戲說明, 存到 <game>/guide.md。
寫完回報: 待定項目有幾個、各是什麼原因; 說明分幾頁、每頁一句話講什麼
```

退回重寫(round.spec-draft > 1):
```
狀態: spec-draft, 規格第 <N> 版
請讀取: <game>/decisions.md、<game>/archive/spec.v<N-1>.md、<game>/archive/telemetry.v<N-1>.md(存在才列)、<game>/archive/guide.v<N-1>.md(存在才列)、~/.claude/skills/game-studio/references/guide-principles.md
任務: decisions.md 已修訂, 重點看「修訂紀錄」最後一條, 那是這次改版的原因。以上一版規格為底改出第 <N> 版存到 <game>/spec.md, 沒被修訂影響的章節維持原樣, 不要無故重寫; 上一版沒有「音效清單」章節時照模板補上。「操作」章節只列 decisions.md 選定的那一種輸入。埋點寫在 <game>/telemetry.md(上一版沒有 telemetry.md、埋點還在 spec 裡 → 這版拆出去, spec.md 的「埋點」章節只留一行指向它); spec.md 只寫現行規則, 上一版裡的版本沿革與設計理由(「vN 改了…」「理由: …」這類段落)一律刪掉, 理由已在 decisions.md。規格寫完後, 依 guide-principles.md 寫玩家說明存到 <game>/guide.md: 有上一版說明就以它為底, 只改受影響的頁; 沒有就新寫。
輸出格式: 章節照模板(同上, 標題 v<N>)。寫完回報: 改了哪些章節、對應修訂紀錄的哪一點; 說明改了哪幾頁(或新寫幾頁)
```

## 物理精確型關卡(平台跳躍等)的規格寫法

關卡能不能過取決於跳躍軌跡、碰撞邊緣這類細節時, 不要讓企劃與數值手算邊界定案: 手算邊際常只有 0~0.3 格, 比站位誤差還小, 每輪審查都會挖出新捷徑(2026-10-07 GhostEcho 為此退回兩次)。concept 定案時就在 decisions.md 寫「關卡驗算原則」, prompt 要求企劃每關寫四塊: 設計意圖、預期解的輸入序列、必須不成立的捷徑清單(也寫成輸入序列)、地形初始座標與可調範圍, 並加一節「自動驗證」; build 時 RD 把物理抽成可用 node 逐幀跑的模組, 跑完序列並在可調範圍內調地形, 回報最終座標由你回寫 spec。審查只看原則與清單是否完整, 不爭手算數字。

## 你的檢查(不討論, 只把關格式)

- 章節齊全、「物件清單」沒寫外觀、「待定」不是空的就是有原因、「數值參數表」有畫面尺寸
- 執行守則中標記 spec-draft 的條目(R1: 操作章節只有一種輸入; R2: guide.md 存在, 每頁有標題、文字、圖要示意什麼; R3: telemetry.md 與 decisions.md「埋點」段一致)
- spec.md 沒有殘留版本沿革段落(搜「v<數字> 改」「理由」等字樣抽查)
- 格式不對 → SendMessage 同一個 agent 要他修, 不重 spawn
- 內容好壞不在這裡判, 那是 spec-review 的事

## 轉移

本次無檔案要搬 archive。照 SKILL.md 轉移程序 → `spec-review`。回報使用者: 規格第 N 版落地、待定幾項。
