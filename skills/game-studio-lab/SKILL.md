---
name: game-studio-lab
description: 遊戲玩法驗證流水線(LangGraph)。使用者要做遊戲 demo、遊戲原型、驗證一個遊戲玩法、把遊戲點子做成可以玩的, 或輸入 /game-studio-lab、提到 game-studio-lab、指向一個含 .lab/ 的專案資料夾時使用。相近說法如「做個小遊戲試試」「用 lab 流程做這個玩法」「繼續上次的遊戲」「我玩過了給回饋」。
---

# game-studio-lab

用 LangGraph 串起來的試玩版流水線。每輪同時做 2~3 款(打磨階段 1 款), 試玩後由你訪談使用者, 用回饋去驗證「機制 → 體驗」的假設, 結果累積在專案的 `hypotheses.md`。

完整設計見 `docs/2026-10-06-game-studio-lab-design.md`。分工:
- **LangGraph 流程**(`lab/`): 設計、美術、RD、音效、接合檢查、錯誤判定、檢討假設, 各節點起無頭 `claude -p` 去做, 自動 commit + push
- **你**(這份 skill): 開場收資料、啟動 / 接續流程、試玩訪談、把回饋寫成檔案交回流程

你不寫遊戲、不改 hypotheses.md、不手動 commit, 這些都是流程的事。

## 指令

一律在 skill 資料夾下執行(`-m lab` 才找得到套件):

```
cd ~/.claude/skills/game-studio-lab && .venv/Scripts/python -m lab <子指令> ...
```

| 子指令 | 用途 |
|---|---|
| `start <專案> --idea-file <檔> --repo <url>` | 建專案並跑第一輪探索 |
| `resume <專案> --choice <選擇> --feedback <檔> [--target <款>]` | 交回饋並接著跑 |
| `resume <專案>` | 上次出錯停下, 修好後從失敗的節點接著跑 |
| `status <專案>` | 查目前停在哪 |
| `release <資料夾> --info <檔>` | 非 lab 專案(遊戲在 `<資料夾>/game/`, 例: 捕泡手)的發布; 停在挑選頁後用 `--choice pick --feedback <檔>` 或 `--choice redo`; 中途出錯修好後不帶參數接續 |
| `probe-models` | 每種節點用正式參數起一次極短 session, 回報實際用到的模型(改了模型設定或 managed settings 後用) |

- `.venv` 不存在(新機器)→ 先 `python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt`
- `start` / `resume` 一輪要跑幾十分鐘: **一律用 Bash 的 run_in_background 執行**, 完成時會收到通知, 不要輪詢。等待期間告訴使用者大概要等多久即可
- stdout 最後一行是狀態 JSON, `status` 有五種: `waiting_feedback`、`build_failed`、`waiting_release_pick`、`done`、`error`; `warnings` 非空(例如 push 失敗)要原文轉告使用者

## 開場

1. 使用者給了專案資料夾且裡面有 `.lab/` → 跑 `status`, 依狀態接手(見下), 回報一句「目前在 X 階段第 N 輪, 狀態是 Y」
2. 新專案 → 跟使用者要三樣東西(缺哪樣問哪樣): **遊戲想法**、**git repo 網址**(需是空的 repo)、**本地資料夾位置**(不存在或空資料夾)
3. **啟動前先確認核心體驗**: 核心體驗是使用者最想讓玩家感受到的那一兩件事, 每款都要圍著它做, 其餘一切都可以有不同設計方向。不叫使用者自己下定義, 由你發問釐清, 例:
   - 「玩家最爽的一刻是什麼畫面?」「玩到什麼情況你會覺得這不是你要的遊戲?」
   - 想法裡寫了不只一種體驗、而且可能互相拉扯時(例: 「慢慢想組合的策略」與「節奏緊湊考驗反應」), 點出來問哪個是核心, 或兩者怎麼共存
   問完把核心體驗整理成一兩句給使用者確認; 同時講明探索試玩只驗核心體驗, 跨關卡的外層系統(例: 大地圖、評價、解鎖)不做。不在這一步提探索方向或假設, 那是設計節點的事
4. 把遊戲想法**原文照錄**寫到 scratchpad 的暫存檔, 後面接一段 `## 核心體驗`(使用者確認的那一兩句, 加上訪談中問出的「不要的體驗」), 用 `start` 啟動

## 依狀態處理

### waiting_feedback: 請使用者試玩, 然後訪談

1. 列出每款的 `index_html` 絕對路徑(可直接雙擊)。不重寫操作說明: 探索 / 深掘的遊戲開場有說明頁, 打磨是開始畫面 + 嵌入在遊戲流程裡的新手教學(打磨沒有說明頁)
2. 讀 `<專案>/<round_dir>/*/spec.md` 的概述與 `hypotheses.md` 的「各款對應」, 心裡有底每款在驗什麼; **不要把假設念給使用者聽**, 免得引導他的感受。同時記下假設表裡狀態「成立」的每條「機制 → 體驗」(好壞都算), 下一步要對照
3. 照該階段的訪談指引進行: `references/interview-explore.md` / `interview-deepen.md` / `interview-polish.md`
4. **對照已成立的假設**: 使用者的回饋若和任一條成立的「機制 → 體驗」相反(例: 已成立「限時拆裝 → 緊張刺激」, 這次卻說限時拆裝很煩), 當場提醒, 用白話講出那條是哪一輪、因為什麼回饋成立的, 並問屬於哪種:
   - **改變想法**: 使用者現在不要 / 改要這個體驗了 → 該假設要翻案
   - **情境不同**: 同一機制換了搭配(數值、節奏、其他機制)效果就變了 → 原假設保留, 補上成立的條件
   - **其實不衝突**: 講的是別的機制或細節 → 照常記
   提醒是為了不讓已驗證的結論被無聲推翻, 不是要說服使用者維持原判; 使用者怎麼答就怎麼記。答案寫進 feedback.md 的「與已成立假設的衝突」段
5. 訪談中使用者回報 bug(當掉、操作沒反應、說明與實際不符)→ 寫成 `<round_dir>/bugs-<款>-<n>.md`, `resume --choice fix --feedback <該檔> --target <款>`; 修完會再停在 waiting_feedback, 請他重玩那款再繼續訪談
6. 訪談最後問繼續或往下一階段, 把訪談整理成 `<round_dir>/feedback.md`(格式見 `references/feedback-template.md`), 給使用者看一眼確認沒誤解, 然後 `resume --choice <選擇> --feedback <round_dir>/feedback.md`

可選的 `--choice`(狀態 JSON 的 `allowed_choices` 也會列):

| 階段 | continue | next | back-deepen / back-explore | end |
|---|---|---|---|---|
| 探索 | 再探索一輪 | 進深掘 | — | 結束 |
| 深掘 | 再深掘一輪 | 進打磨 | — | 結束 |
| 打磨 | 再打磨一輪 | — | 退回深掘 / 探索 | 結束 |

打磨另有 `release`(發布, 見下方「發布」), 訪談最後問「再打磨、退回、結束, 還是發布」。

打磨階段固定在 `<專案>/polish/` 迭代(round_dir 永遠是 `polish`), 進入打磨後探索 / 深掘的資料夾會被流程刪除(git 有紀錄)。因為每輪共用同一個資料夾, 打磨第 N 輪(N ≥ 2)的回饋檔改叫 `feedback-N.md`, 免得蓋掉前幾輪的回饋。

打磨階段 resume 之前: 到 `~/Downloads` 把本輪的 `gamelog-<專案資料夾名>-*.json` 搬到 `<round_dir>/logs/round-N/`(N = 打磨第幾輪, 只搬不整理); 一個都沒有就在回饋檔註明。

### 每次流程停下來後: 經驗收件匣與規格同步

- **經驗收件匣**: 無頭 `claude -p` 改不了 `~/.claude` 底下的檔(會被權限擋下, 直接回寫的經驗都會遺失), 所以節點把經驗提案寫到 `<專案>/.lab/lessons-inbox/<目標檔名>`。每次流程停下來, 你就審收件匣: 照目標經驗文件的規則(只收跨遊戲通則、先找同類合併、art-lessons 的理念升降規則)併進本 skill 的 `references/`, 不合格的丟掉; 處理完刪掉收件匣檔案, 照 commit 規範 commit `~/.claude`(系統名 `game-studio-lab`)。在專案裡的收件匣檔不必另外 commit 刪除, 下一次流程跑完會一起 commit
- **規格同步**: RD(含修 bug)不改 spec.md。回報裡若列出「規格要同步的內容」(例: 修 bug 加了關卡物件), 由你照它更新 `<round_dir>/<款>/spec.md`, 讓下一輪設計讀到的是實際狀態

### 發布: 產出網站用的遊戲與素材

把定版遊戲與 PVD計畫網站要的素材做成 `<專案>/release/`(`game/` 網站版遊戲、`assets/` 定版素材、`options/` 方案與選擇頁)。設計見 `docs/2026-10-29-release-stage-design.md`, 兩個使用者檔的格式見 `references/release-guide.md`。

1. **問使用者三樣**, 寫成發布資訊檔(lab 專案 `polish/release-info.md`; 非 lab 專案 `<資料夾>/release-info.md`):
   - **遊戲名稱**: 使用者提供。名稱定了就全部統一, 流程會把遊戲開始畫面(打磨版與網站版都改)、預覽圖、素材資訊都換成這個名稱, 先先講明
   - **遊戲介紹**: 使用者提供, 1–2 句、30–60 字; 超出或太短提醒使用者, 不代改
   - **遊戲代號**(網址用, 上線後不改): 你帶預設給使用者確認, 依序取上次 `release/assets/素材資訊.md` 的代號 → PVD計畫網站 repo 的 `site/js/games.js` 裡該遊戲已定的 `code`(本機例: `E:\Project\PVDWebsite`; 找不到 repo 就跳過這項) → 由專案名轉英文小寫加連字號
2. lab 專案: `resume <專案> --choice release --feedback <發布資訊檔>`; 非 lab 專案: `release <資料夾> --info <發布資訊檔>`。都要背景執行, 約十幾到三十分鐘。選發布不跑檢討假設: 這輪若有試玩回饋要進下一輪設計, 應選 continue
3. 停在 `waiting_release_pick`: 把 `options_page`(選擇頁絕對路徑, 只能看不能操作)給使用者, 請使用者回代號(例「圖示 B、主色 2、預覽圖 A」)。寫成 `release-pick.md`(放發布資訊檔旁), `--choice pick --feedback <檔>`; 都不喜歡 → `--choice redo`(只重做美術方案, 可把使用者的意見寫進 `release/options/redo-notes.md` 給美術看)
4. 定版完: lab 專案回到同一個打磨停點(`waiting_feedback`, 遊戲不重做), 可再選 continue / back-* / end / release; 非 lab 專案流程結束。回報 `release/` 路徑與 `warnings`(例: 檔案超過網站 25MB 上限)

不做: 手機版、鍵名格式、網站暫停 / 繼續訊息、改 PVDWebsite repo(網站另外更新)。

### build_failed: 有款做不出來

`failed` 列出每款的錯誤。轉述給使用者(用白話, 不貼原始 JSON), 讓他選:
- `retry`: 再給錯誤判定兩次機會(不從頭重做)
- `skip`: 本輪不要這款, 其他款照常進試玩

### error: 流程中途停下

`error` 是錯誤原文。判斷原因: 是環境問題(權限、網路、claude 登入)→ 請使用者處理後 `resume <專案>`; 是程式問題 → 修 `lab/` 後 `resume`; 不確定 → 原文給使用者看並說你的判斷。已完成的節點不會重做。

### paused: 流程行程被中途砍掉

`status` 回 `paused` 表示流程沒停在暫停點也沒報錯, 是行程本身被終止(例: Claude Code 在記憶體不足時砍掉背景指令)。已完成的節點都在進度檔裡, 不會重做。被砍掉的背景指令不要自己重跑, 告訴使用者停在哪、為什麼, 等他說要繼續再 `resume <專案>`(不帶 choice)。重跑前可查有沒有殘留的 `claude -p` 行程。

最常見的原因是製作階段同時起多個 `claude -p`(美術、RD 等各款並行)吃光記憶體。

### done

回報總結: 跑了幾輪探索 / 深掘 / 打磨, `hypotheses.md` 裡確認了哪些想要 / 不要的體驗、保留與避開的機制。

## 權限

流程會起無頭 `claude -p`, 工具限縮在讀寫檔與少數指令(見 `lab/runner.py`), 不用 bypassPermissions。若 Claude Code 擋下 `python -m lab` 的執行, 請使用者在 settings 加允許規則, 不要繞過。

## 維護

- 跑這個 skill 途中學到的事(踩坑、限制、必要步驟)寫回本檔或對應參考檔, 不寫 memory
- 改了 `lab/` 或 `check/` 之後跑 `.venv/Scripts/python -m pytest`
- AI 節點的任務內容在 `prompts/`; 每種任務的模型與工具在 `lab/runner.py`
