---
name: game-studio-lab
description: 玩法驗證流水線(game-studio 的 LangGraph 改版, 與原版並存)。使用者輸入 /game-studio-lab、提到 game-studio-lab、要用「探索 / 深掘 / 打磨」流程一次產出多款試玩版驗證玩法、或指向一個含 .lab/ 的專案資料夾時使用。相近說法如「用 lab 流程做這個玩法」「lab 那款我玩過了」。
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
| `probe-models` | 每種節點用正式參數起一次極短 session, 回報實際用到的模型(改了模型設定或 managed settings 後用) |

- `.venv` 不存在(新機器)→ 先 `python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt`
- `start` / `resume` 一輪要跑幾十分鐘: **一律用 Bash 的 run_in_background 執行**, 完成時會收到通知, 不要輪詢。等待期間告訴使用者大概要等多久即可
- stdout 最後一行是狀態 JSON, `status` 有四種: `waiting_feedback`、`build_failed`、`done`、`error`; `warnings` 非空(例如 push 失敗)要原文轉告使用者

## 開場

1. 使用者給了專案資料夾且裡面有 `.lab/` → 跑 `status`, 依狀態接手(見下), 回報一句「目前在 X 階段第 N 輪, 狀態是 Y」
2. 新專案 → 跟使用者要三樣東西(缺哪樣問哪樣): **遊戲想法**、**git repo 網址**(需是空的 repo)、**本地資料夾位置**(不存在或空資料夾)
3. 把遊戲想法**原文照錄**寫到 scratchpad 的暫存檔, 用 `start` 啟動

## 依狀態處理

### waiting_feedback: 請使用者試玩, 然後訪談

1. 列出每款的 `index_html` 絕對路徑(可直接雙擊)。不重寫操作說明, 遊戲開場的說明畫面就是給他看的
2. 讀 `<專案>/<round_dir>/*/spec.md` 的概述與 `hypotheses.md` 的「各款對應」, 心裡有底每款在驗什麼; **不要把假設念給使用者聽**, 免得引導他的感受
3. 照該階段的訪談指引進行: `references/interview-explore.md` / `interview-deepen.md` / `interview-polish.md`
4. 訪談中使用者回報 bug(當掉、操作沒反應、說明與實際不符)→ 寫成 `<round_dir>/bugs-<款>-<n>.md`, `resume --choice fix --feedback <該檔> --target <款>`; 修完會再停在 waiting_feedback, 請他重玩那款再繼續訪談
5. 訪談最後問繼續或往下一階段, 把訪談整理成 `<round_dir>/feedback.md`(格式見 `references/feedback-template.md`), 給使用者看一眼確認沒誤解, 然後 `resume --choice <選擇> --feedback <round_dir>/feedback.md`

可選的 `--choice`(狀態 JSON 的 `allowed_choices` 也會列):

| 階段 | continue | next | back-deepen / back-explore | end |
|---|---|---|---|---|
| 探索 | 再探索一輪 | 進深掘 | — | 結束 |
| 深掘 | 再深掘一輪 | 進打磨 | — | 結束 |
| 打磨 | 再打磨一輪 | — | 退回深掘 / 探索 | 結束 |

打磨階段 resume 之前: 到 `~/Downloads` 把本輪的 `gamelog-<專案資料夾名>-*.json` 搬到 `<round_dir>/logs/`(只搬不整理); 一個都沒有就在 feedback.md 註明。

### build_failed: 有款做不出來

`failed` 列出每款的錯誤。轉述給使用者(用白話, 不貼原始 JSON), 讓他選:
- `retry`: 再給錯誤判定兩次機會(不從頭重做)
- `skip`: 本輪不要這款, 其他款照常進試玩

### error: 流程中途停下

`error` 是錯誤原文。判斷原因: 是環境問題(權限、網路、claude 登入)→ 請使用者處理後 `resume <專案>`; 是程式問題 → 修 `lab/` 後 `resume`; 不確定 → 原文給使用者看並說你的判斷。已完成的節點不會重做。

### done

回報總結: 跑了幾輪探索 / 深掘 / 打磨, `hypotheses.md` 裡確認了哪些想要 / 不要的體驗、保留與避開的機制。

## 權限

流程會起無頭 `claude -p`, 工具限縮在讀寫檔與少數指令(見 `lab/runner.py`), 不用 bypassPermissions。若 Claude Code 擋下 `python -m lab` 的執行, 請使用者在 settings 加允許規則, 不要繞過。

## 維護

- 跑這個 skill 途中學到的事(踩坑、限制、必要步驟)寫回本檔或對應參考檔, 不寫 memory
- 改了 `lab/` 或 `check/` 之後跑 `.venv/Scripts/python -m pytest`
- AI 節點的任務內容在 `prompts/`; 每種任務的模型與工具在 `lab/runner.py`
