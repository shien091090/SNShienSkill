# game-studio-lab 設計

日期: 2026-10-06
流程圖(含節點說明與文件說明): https://claude.ai/artifact/XyRSAhFQfFD34WXH5Td13D

## 目的

與 game-studio 並存的第二條遊戲流水線, 目的是**快速產出試玩版、驗證新玩法**。核心產物是一份「玩法驗證文件」: 記錄「什麼機制帶來什麼體驗」的假設, 每輪試玩後保留成立的、刪掉推翻的, 最後讓玩家想要 / 不要的體驗與對應機制一目了然。

## 三個階段

| 階段 | 每輪款數 | 設計任務 | 訪談重點 | 離開條件 |
|---|---|---|---|---|
| 探索 explore | 2~3 | 分析玩法可能帶來的體驗, 每款主打一種; 使用者給的玩法全保留, 另加強化該體驗的機制; 機制 → 體驗寫成假設 | 哪款體驗最好、是什麼體驗、不好的體驗、來源 | 使用者說探索夠了 |
| 深掘 deepen | 2~3 | 照驗證文件「保留 / 避開」清單, 用不同新機制強化同一種目標體驗; 新機制也是假設 | 喜歡 / 不喜歡哪些機制、為什麼 | 使用者說玩法定案 |
| 打磨 polish | 1 | 以深掘勝出款(或上一版打磨)為底, 定關卡數、加埋點(看難度曲線)、加音效 | 自由回饋; 回饋若在改玩法, 指出並建議退回 | 使用者說結束, 或退回深掘 / 探索 |

探索與深掘不考慮難度, 有關卡只做一關。每款只用一種操作(只滑鼠或只鍵盤)。玩家說明: 探索與深掘用開場說明頁(guide.md); 打磨沒有說明頁, 改為開始畫面 + 嵌入遊戲流程的新手教學(spec「新手教學」表, 每個新東西第一次出現時才教, 玩家做到動作才算完成; 2026-10-09 修訂)。

## 架構

三層:

1. **入口 skill** `/game-studio-lab <資料夾>`(`SKILL.md`): 跟使用者對話 — 開場收「遊戲想法 + git repo 網址 + 本地資料夾」、試玩訪談、問繼續或往下一階段。透過 CLI 啟動 / 續跑 LangGraph, 流程在背景跑, 完成時 Claude Code 收到通知。
2. **LangGraph 流程**(`lab/` Python 套件): 只管順序、分支、狀態。進度存 `<專案>/.lab/checkpoint.sqlite`(進 git, 換機器可接), thread_id 固定 `main`。
3. **工作節點**: AI 節點各起一個無頭 `claude -p` 讀寫專案資料夾; 美術 / RD / 音效用 `--agent game-artist|game-rd|game-audio`, 沿用現有 agent 定義。權限採**限縮工具清單**(`--allowedTools` 列出 Read / Write / Edit / Glob / Grep 與必要的 Bash 指令), 不用 bypassPermissions。

### 節點

| 節點 | 種類 | 說明 |
|---|---|---|
| setup | 程式 | 建資料夾、git init、設 remote、寫 idea.md / STATE.md / hypotheses.md 骨架、第一次 commit + push。遠端已有內容或資料夾非本流程建立 → 報錯停下 |
| design | AI | 依階段寫本輪假設進 hypotheses.md, 每款寫 spec.md、interface.json、guide.md |
| build_game | 子圖 | 對每款用 Send 分岔, 子圖內: art ∥ rd(∥ audio, 僅打磨)→ check → (不過) triage → 退回對象 → check ... |
| art / rd / audio | AI | 照 interface.json 實作; RD 在美術未交付前用方塊佔位 |
| check | 程式 | 接合腳本(Node, 見下) |
| triage | AI | 只在 check 不過時跑: 讀錯誤報告與雙方程式, 決定退回誰、怎麼改。每款最多 2 次, 用完 → halt |
| halt | 暫停 | interrupt 回報建置失敗; 使用者選 retry(重置次數再跑)或 skip(本輪丟掉這款) |
| interview | 暫停 | interrupt, 由入口 skill 在對話中訪談; 回傳 feedback 檔路徑與選擇 |
| fix | AI | 訪談中回報的 bug: RD 修指定款, 修完跑 check, 回到 interview |
| review | AI | 依 feedback 把每條假設標成立 / 推翻 / 不確定, 更新 hypotheses.md(舊版先存 archive); 打磨另讀試玩紀錄寫難度曲線分析 |
| route | 分支 | 依選擇: continue(本階段再一輪)/ next(下一階段)/ back-deepen / back-explore(僅打磨)/ end |

同時跑的 claude 數上限: `max_concurrency=6`。

### 繪圖介面 interface.json

由 design 寫在每款遊戲資料夾, 美術與 RD 共同遵守的契約, 也是接合腳本的檢查依據。美術不能改函式名與欄位, 只決定畫法。

```json
{
  "canvas": { "width": 720, "height": 1280 },
  "draw": [
    { "name": "drawBackground", "state": [] },
    { "name": "drawPlayer", "state": ["x", "y", "hit"], "size": [48, 48] }
  ],
  "guidePages": 2,
  "sounds": ["hit", "clear"],
  "music": ["main"]
}
```

`sounds` / `music` 只在打磨階段出現。`drawGuidePage(ctx, state)` 永遠存在, 不必列。

### 接合腳本 check.js

game-studio 已禁止自測開瀏覽器(殘留的無頭行程會在背景播音樂), 所以接合腳本用 **Node vm + 假 DOM / 假 canvas**, 不開任何瀏覽器:

1. 依 index.html 的 script 順序載入 art.js →(有就載)sound.js → game.js; 任何拋錯 → 失敗
2. `window.Art` 有 interface.json 列的每個函式與 `drawGuidePage`; 逐一用假 ctx 與依欄位造的假 state 呼叫, 不拋錯
3. game.js 裡呼叫的 `Art.drawXxx` 都在介面內(靜態掃描)
4. 打磨: `window.Sound` 有 `play` / `playMusic` / `init`, game.js 播放的事件名都在 `sounds` / `music` 內
5. 模擬 300 幀 requestAnimationFrame, 期間對已註冊的輸入監聽送幾次合成事件, 不拋錯
6. index.html 宣告 utf-8

輸出 JSON `{ ok, errors: [{ step, message }] }`。

### 驗證文件 hypotheses.md

```
# 玩法驗證文件
## 核心玩法(使用者指定, 每款都必須有)
## 已確認的體驗
### 想要
### 不要
## 機制清單
### 保留
### 避開
## 假設表
| 編號 | 機制 | 預期體驗 | 正/負 | 來源 | 驗證於 | 狀態 |
## 各款對應
| 輪次 | 款 | 主打體驗 | 驗哪幾條 |
## 修訂紀錄
```

狀態: 待驗 / 成立 / 推翻 / 不確定。成立 → 留表並寫進保留或避開清單; 推翻 → 從表刪除, 修訂紀錄留一行(刪了哪條、為什麼); 不確定 → 留表待下一輪換做法驗。「某機制帶來壞體驗」成立時是有價值的結論, 進「避開」, 不刪。

### 專案資料夾

```
<專案>/
  STATE.md  idea.md  hypotheses.md
  .lab/            checkpoint.sqlite、logs/(每次 claude -p 的輸出)
  explore-1/
    feedback.md
    logs/          打磨階段的試玩紀錄 JSON
    game-a/        spec.md、interface.json、guide.md、game/(index.html、game.js、art/、audio/)
  archive/         hypotheses.v<N>.md
```

打磨階段(2026-10-09 修訂):
- 固定在 `polish/game/` 一個資料夾迭代, 不再每輪開 `polish-<N>`。每輪開始前清掉上一輪的完成標記與檢查結果, 美術 / RD / 音效在既有產物上修改
- 進入打磨、設計交稿後, 刪除所有 `explore-*`、`deepen-*`、`polish-<N>` 資料夾(git 留有紀錄); 驗證文件與 archive 保留
- `polish/feedback.md`、`polish/difficulty.md` 每輪覆寫(每版都已 commit); 試玩紀錄在 review 用完後收進 `polish/logs/round-<N>/`

### git

專案資料夾自動 commit + push(使用者授權, 只限本流程建立的專案資料夾)。commit 不在節點裡做, 由 CLI 在每次流程停下來(暫停點、完成、出錯)後統一做: 先關掉進度檔連線讓 WAL 寫回, commit 進去的才是完整進度。格式照 `~/.claude/rules/commit-format.md`, 系統名稱用專案資料夾名。push 失敗不 force, 狀態 JSON 帶 warning 回報使用者。

### 經驗文件

美術 / RD / 音效讀 game-studio 的 `references/{art,rd,audio}-lessons.md`, 收工時照該檔規則寫回; 寫回前先重新讀檔(同時可能有別款在寫)。

### CLI(入口 skill 呼叫)

```
.venv/Scripts/python -m lab start  <專案> --idea-file <檔> --repo <url>
.venv/Scripts/python -m lab resume <專案> --choice <continue|next|back-deepen|back-explore|end|fix|retry|skip> [--feedback <檔>] [--target <款>]
.venv/Scripts/python -m lab status <專案>
```

stdout 最後一行為 JSON: `{ status: waiting_feedback | build_failed | done | error, stage, round, round_dir, games: [{ id, index_html }], warnings, error }`。

`LAB_FAKE_CLAUDE=1` 時 AI 節點改用假執行器(寫固定內容的檔案), 供測試。

### 錯誤處理

- 單款子圖中途有角色當掉時, LangGraph 接續會重跑整個子圖; 所以美術 / RD / 音效交付成功後在款資料夾留 `.done-<角色>` 標記, 接續時看到就跳過
- 任何節點拋錯 → 流程停在該節點, CLI 回 `status: error` 與錯誤原文; 修好後 `resume`(不帶 choice)從失敗節點重跑
- `claude -p` 非零結束或逾時(預設 40 分鐘)→ 拋錯
- 每次 claude -p 的完整輸出存 `.lab/logs/`

## 驗證

- 流程走向: 假執行器跑整張圖, pytest 覆蓋每條分支(continue / next / back / end / fix / halt-retry / halt-skip)
- 中斷接回: 每個暫停點後重新建圖接續, 確認不重做已完成節點
- 接合腳本: 一款正確樣本 + 數款故意弄壞的樣本, 好的過、壞的都抓到
- 實際試跑: 用簡單玩法跑完一輪探索, 使用者試玩並走一次訪談

## 實作步驟

1. 環境: skill 資料夾內建 `.venv`(不進 git)安裝 langgraph、langgraph-checkpoint-sqlite、pytest; `requirements.txt`
2. 流程骨架 + 假執行器 + CLI, 通過流程測試
3. 接合腳本 + 樣本測試
4. AI 節點的 prompt 與真實執行器
5. SKILL.md 與三階段訪談指引
6. 實際試跑一輪
