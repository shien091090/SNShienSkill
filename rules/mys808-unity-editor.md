---
paths:
  - "D:/Git/MYS-808/**"
---

# MYS-808 Unity Editor 操作

透過 Unity MCP 編譯或跑測試時的規矩。

## 觸發編譯前先確認不在 Play

`AssetDatabase.Refresh()` 或任何會觸發腳本重編的動作之前，先查 Editor 狀態（`Unity_ManageEditor` GetState），`IsPlaying` 為 true 就停手，請使用者先停止 Play。

**Why:** 2026-10-05 在使用者 Play 中觸發重編，Play 中重載花了 191 秒，`ChatSnapshotView.Update` 因 presenter 遺失每幀噴 NullReferenceException，log 衝到 600MB，MCP 連線卡死，要使用者手動 `/mcp` 重連。

## 跑 EditMode 測試一律排除 OdinValidatorTest

`SCGLobby.Tests.OdinValidator.OdinValidatorTest` 會掃整個專案，一跑就很久。跑「全部」EditMode 測試時用 groupNames 排除它，例如 `^(?!SCGLobby\.Tests\.OdinValidator\.).*`；只在使用者明確要求時才跑。

**Why:** 2026-10-06 使用者要求：「不要跑 odin validator 的測試，他一跑就會跑超久」。

## 測試結果用 TestFinished 過濾後逐筆寫檔

`RegisterCallbacks` 註冊的 callback 跨次執行都還在，也會收到使用者在 Test Runner 視窗自己跑的那輪。只在 `RunFinished` 把整份結果寫到固定檔名，可能讀到別輪的結果。改成在 `TestFinished` 依 FullName 前綴過濾、append 到這次專用的檔名，並以 `RunFinished` 寫一行結束標記。

**Why:** 2026-10-08 跑贈禮測試，連三次讀到的都是 `SR_HistoryHandlerTest` 那輪的結果（pass=20），新測試根本不在裡面。

## 啟動測試時保留 run guid

`TestRunnerApi.Execute` 回傳的 guid 要記下（例如寫進 log 或結果檔），需要中斷時用 `TestRunnerApi.CancelTestRun(guid)`。這版測試框架沒有 `CancelAllTestRuns` / `GetActiveRunGuids`，沒存 guid 就無法中斷。
