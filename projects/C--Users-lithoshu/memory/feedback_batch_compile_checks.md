---
name: feedback-batch-compile-checks
description: 開發 Unity 功能時，不要頻繁檢查編譯狀態；等測試與模塊功能都完整實作完後，才一次確認編譯並跑測試
metadata:
  node_type: memory
  type: feedback
  originSessionId: 176f2d81-e077-4c2f-9332-ac215d7b56de
---

用 Unity MCP 開發功能（尤其是多步驟的模塊拆解/實作流程）時，不要每建立一個檔案、每寫完一小段就呼叫 `refresh_unity`/`read_console` 確認編譯狀態。應該等一輪要做的東西（unit test + production class + 任何輔助資料結構）全部寫完後，才一次檢查編譯並用 `run_tests` 跑測試。

**Why:** 使用者認為頻繁確認編譯狀態是不必要的中斷，編譯失敗與否本來就會在跑測試時一併反映出來，沒必要拆成好幾次個別確認。

**How to apply:** 這個原則已經寫進 [[dailyranktournament-decompose-module-progress]] 提到的 `activity-decompose-module` skill 本身（Step 5、Step 8、Step 9 都明確標註不檢查編譯，統一在 Step 11 跟 `run_tests` 一起做），但這個習慣不只限於這個 skill——任何用 Unity MCP 做多步驟開發的場合都應該比照辦理：先把整個邏輯區塊（測試+功能實作+輔助類別）寫完，再一次確認編譯結果，不要每完成一小步就检查一次。
