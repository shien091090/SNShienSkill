# game-studio 設計稿

日期: 2026-09-20
狀態: 待使用者 review

## 目標

以「遊戲製作人」身分帶一組職能 agent, 把使用者的一句概念發想帶到可試玩的網頁 Demo, 並在試玩回饋中反覆迭代。製作人(主 session)負責統整與拍板, 所有遊戲設計決策不問使用者。職能 agent 每次上工都是全新 session, 只靠文件溝通。

## 已定決策

| 題目 | 決定 |
|---|---|
| Demo 技術形態 | 單一 HTML + Canvas + 原生 JS, 零依賴、離線可玩; 美術用程式畫, 不生圖 |
| 討論收斂 | 固定兩回合 + 製作人拍板 |
| 專案位置 / 觸發 | 使用者指定資料夾, `/game-studio <資料夾>`; 不存在就建, 存在就讀 STATE.md 接續 |
| RD 經驗文件 | 跨遊戲共用, 放 skill 目錄隨 `~/.claude` 同步; 只出現在 RD 的輸入清單 |
| 模型 | 企劃、數值、美術 opus; RD sonnet |
| 音效角色 | 本版不建 agent, 流程無其出場狀態; 角色清單列出並註明尚未啟用 |
| 整體結構 | 一個 hub skill + 每狀態一份參考檔 + 4 個 `~/.claude/agents/` 定義 |

不採用的做法與理由:
- 一狀態一 skill: 轉移與退回規則散在多檔易不一致, 且使用者不需手動跳狀態
- Workflow 腳本: 每個節點都需要製作人做設計判斷, 腳本無法承擔

## 一、資料夾與文件結構

```
<game>/
  STATE.md               目前狀態、輪次計數、事件 log
  concept.md             使用者最初概念, 原文照錄, 永不修改
  decisions.md           定案結果文件(現行版), 底部「修訂紀錄」列每次改動與原因
  spec.md                Demo 規格(現行版)
  archive/               被取代的舊版: decisions.v1.md、spec.v1.md ..., 不刪
  discussions/           討論原始紀錄, 一狀態一輪一角色一檔, 例: concept-r1-planner.md
  feedback/              每輪試玩回饋, 例: round-1.md, 內分 bug / 玩法 / 美術三段
  game/
    index.html           可執行網頁遊戲
    game.js / style.css  RD 視需要拆檔
    art/
      art.js             美術交付: Canvas 繪製函式, 每種遊戲物件一個
      style.md           色票、尺寸表、形狀語言
```

- decisions.md、spec.md 永遠只有一份現行版, agent 輸入清單只寫檔名。改版前舊檔搬 `archive/` 加版號
- discussions/ 只寫不讀, 任何 agent 的輸入清單不含它
- feedback/ 由製作人在 playtest 邊收邊寫
- RD 經驗文件在 `~/.claude/skills/game-studio/references/rd-lessons.md`, 不在遊戲資料夾

STATE.md 格式:

```
state: spec-review          // concept | spec-draft | spec-review | build | playtest | done
round:
  spec-draft: 2             // 規格第幾版, 退回一次 +1
  playtest: 1               // 第幾輪試玩
log:
- 2026-09-20 concept 定案, decisions.md v1
- 2026-09-21 spec-review 退回, 理由: 資源循環數值撐不住 10 分鐘
```

## 二、狀態機與轉移規則

```
concept ─定案─▶ spec-draft ─輸出spec─▶ spec-review ─通過─▶ build ─可玩─▶ playtest ─使用者說結束─▶ done
                   ▲                       │                  ▲            │
                   │      退回(修decisions) │                  │ bug/美術回饋 │
                   └───────────────────────┘                  └────────────┘
                   ▲                                                       │
                   └──────────────── 玩法回饋(修decisions) ─────────────────┘
```

| 狀態 | 進入時做 | 離開條件 | 去哪 |
|---|---|---|---|
| concept | 讀 concept.md, 兩回合三方討論 | 製作人寫出 decisions.md | spec-draft |
| spec-draft | 企劃產 spec.md | spec.md 落地 | spec-review |
| spec-review | 兩回合三方討論 | 製作人判定通過 | build |
| | | 判定退回: 修 decisions.md, 舊 spec 進 archive | spec-draft |
| build | 美術先、RD 後 | game/index.html 可執行且 RD 自測通過 | playtest |
| playtest | 收使用者回饋 | bug → RD 修, 不轉移 | playtest |
| | | 美術回饋 → 確認本輪講完 → 修 | build(只跑美術修正 + RD 整合, 不重做) |
| | | 玩法回饋 → 確認本輪講完 → 修 decisions.md | spec-draft |
| | | 使用者說結束 | done |

規則:
- 狀態轉移是製作人唯一直接動手時刻: 更新 STATE.md、搬 archive、寫 log, 三件一起做
- 退回 spec-draft 時, decisions.md 修訂紀錄必須寫改了什麼、觸發自哪個狀態的哪個問題
- 同一輪回饋混三類: 先修 bug 讓使用者能繼續玩; 美術與玩法收齊後只走玩法退回路徑, 美術回饋留在 feedback 檔, 下次 build 一併給美術
- 每次進入任何狀態先讀 STATE.md, 與資料夾實況比對, 有衝突回報使用者裁決, 不自己猜
- 兩回合討論規則寫在 SKILL.md 共通原則, concept 與 spec-review 共用:
  - r1: 兩位 agent 各自獨立看輸入檔給意見
  - r2: 製作人整理「對方重點 + 分歧點 + 製作人追問」, 用 SendMessage 續同 session 丟回去; 不轉貼對方原文
  - 之後製作人統整拍板, 結論寫進 decisions.md(或判定 spec 通過/退回)
  - 跨狀態一律重新 spawn, 不續 session

## 三、各狀態 agent 輸入契約

原則: 每個 agent 拿到的是「檔案清單 + 一段任務指令」, 製作人不得夾帶清單外內容。

| 狀態 | agent | 輸入檔 | 任務指令要點 | 輸出 |
|---|---|---|---|---|
| concept r1 | 企劃、數值(獨立) | concept.md | 從職能角度評估: 核心循環是否成立、Demo 可驗證什麼、最大風險 | 意見 → discussions/ |
| concept r2 | 同兩位(續 session) | 無新檔 | 製作人整理的重點 + 分歧 + 追問 | 回應 |
| spec-draft | 企劃(新) | decisions.md; 退回重寫時加 archive 上一版 spec | 只寫玩法: 核心循環、規則、操作、勝負/結束條件、數值參數表、Demo 範圍邊界; 排除美術與音效; 退回重寫重點看修訂紀錄 | spec.md |
| spec-review r1 | 企劃(新)、數值 | decisions.md、spec.md | 企劃: 是否忠實對應定案、有無漏洞; 數值: 參數表能否撐起目標體驗、有無崩壞點 | 意見 |
| spec-review r2 | 同兩位 | 無新檔 | 同 concept r2 | 回應 |
| build 美術 | 美術 | spec.md | 產 art.js + style.md; 程式畫, 不生圖 | game/art/ |
| build RD | RD | spec.md、game/art/style.md、rd-lessons.md; art.js 直接引用 | 實作 index.html 呼叫 art.js; 缺圖形用幾何佔位並列在回報; 排除障礙後回寫 rd-lessons.md | game/ |
| build 美術修正 | 美術(新) | spec.md、style.md、feedback/round-N.md 美術段 | 只改 art.js / style.md, 不碰邏輯 | game/art/ |
| playtest 修 bug | RD(新) | rd-lessons.md、製作人整理的 bug 描述、game/ | 重現 → 修 → 自測 → 回寫 rd-lessons.md | game/ |

- build 順序美術先 RD 後; 美術產出前不 spawn RD
- 美術修正不得改變既有繪製函式的名稱與參數, 只改內部畫法; 因此美術修正後通常不需 RD 出場。若美術新增函式或 spec 有變, 才 spawn RD 做整合(輸入同 build RD)
- RD 修 bug 一次一批, 一輪的 bug 整理成一份描述
- 數值在 build 與 playtest 不出場; 數值調整屬玩法回饋, 走退回路徑

## 四、agent 定義與經驗文件

`~/.claude/agents/`:

| 檔名 | model | tools | prompt 重點 |
|---|---|---|---|
| game-planner.md | opus | Read, Write, Glob, Grep | 企劃。只談玩法與體驗, 不談美術、音效、技術。寫規格時用固定章節模板 |
| game-balance.md | opus | Read, Glob, Grep | 數值。只評估與提參數, 不改文件; 必須給數字與推算, 不接受「感覺」 |
| game-artist.md | opus | Read, Write, Edit, Glob, Grep, Bash | 美術。只產 art.js + style.md, 禁碰邏輯; Canvas 2D 程式繪製, 不生圖、不引外部資源 |
| game-rd.md | sonnet | Read, Write, Edit, Glob, Grep, Bash | RD。單一 index.html 為主、零依賴、離線可跑; 開工讀 rd-lessons.md, 收工回寫; 禁改 spec.md 與 art/ |

共通: prompt 寫明「只看製作人給的檔案清單, 清單外不要去找」。

`references/rd-lessons.md`:
- 每條: 症狀 → 原因 → 解法, 三行內; 分類: Canvas/渲染、輸入、計時/遊戲循環、其他
- RD 收工前檢視有無「卡住又解掉」或「修 bug」, 有就回寫, 同類條目合併
- 製作人不讀不改, 只在 RD 輸入清單帶它

Skill 佈局:

```
~/.claude/skills/game-studio/
  SKILL.md                      狀態機、轉移表、資料夾結構、討論規則、開場檢查、角色清單
  references/
    state-concept.md
    state-spec-draft.md
    state-spec-review.md
    state-build.md
    state-playtest.md
    templates.md                STATE.md / decisions.md / spec.md / feedback 章節模板
    rd-lessons.md
  docs/                         本設計稿與後續實作計畫
~/.claude/agents/
  game-planner.md  game-balance.md  game-artist.md  game-rd.md
```

## 開場檢查(每次 /game-studio 呼叫)

1. 拿資料夾路徑, 沒帶就問
2. 資料夾不存在 → 建立, 問使用者概念發想, 寫 concept.md, STATE.md 設 concept
3. 存在 → 讀 STATE.md, 與實況比對; 衝突回報裁決
4. 讀 `references/state-<state>.md`, 照它執行
5. 回報一句: 「目前在 X 狀態, 規格第 N 版, 第 M 輪試玩」

## 測試方式

- 用一個極簡概念(例: 「一顆球躲方塊」)冷跑整條流程到 playtest, 確認每個狀態的檔案落地與 STATE.md 轉移正確
- 故意在 spec-review 判退一次, 確認 archive 版號與修訂紀錄
- 在沒用過的工作目錄下 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 冷跑, 確認 skill 不依賴本機 memory
