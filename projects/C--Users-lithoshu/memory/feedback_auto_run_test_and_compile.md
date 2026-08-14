---
name: feedback-auto-run-test-and-compile
description: 之後在 Lobby 專案改完程式碼後，可自動用 Unity MCP 執行 Test Runner 與重新編譯確認，測試全過就直接 commit，不需要每次先詢問
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 15e18882-8c0e-40af-8912-82de8371aa85
  modified: 2026-08-04T06:02:38.346Z
---

在 Lobby 專案（Slot_Lobby）改完程式碼後，可以自動呼叫 Unity MCP 的 `run_tests`/編譯確認流程，不需要每次動作前先問使用者「要不要跑測試」。測試全部通過、確認沒有問題後，直接 commit（不用再問一次），commit message 格式遵循 [[feedback_auto_commit_format]]。

**Why:** 使用者已明確表示「接下來你都可以自動幫我執行 test runner 以及重新編譯」，之後（2026-08-04）進一步表示「之後都請幫我跑一次test runner, 沒問題就幫我commit」——這是對後續工作階段的標準授權，不是單次同意，涵蓋「跑測試」到「commit」這整段流程。

**How to apply:** 完成一輪功能/模塊實作、bugfix 或其他程式碼異動（測試 + production code）後：
1. 直接呼叫 Unity MCP 執行編譯確認與 `run_tests(mode="EditMode")`，不用先徵詢許可；但仍遵守 [[feedback_batch_compile_checks]] 的節奏——等整輪邏輯都寫完再一次跑，不要每改一小段就跑一次
2. 測試全過、確認是真的編譯進新程式碼在跑（不是像 2026-08-04 那次「編譯失敗卻拿舊組件跑測試、數量沒變化又全過」的假象，需要先看 `read_console` 有無 error）後，直接 `git commit`（遵循 [[feedback_auto_commit_format]] 的前綴/標籤格式），不用再問一次「要不要commit」
3. 仍然不 push（[[feedback_no_auto_push_except_gas_url]]）
4. 若 Unity MCP 這個工作階段尚未連線（例如剛啟動、伺服器還在 connecting），需告知使用者無法自動執行，而不是略過驗證直接宣稱完成
5. 若測試沒過，停下來回報失敗內容，不要自己嘗試硬修到過為止就直接commit，除非使用者原本就是要你修到過
