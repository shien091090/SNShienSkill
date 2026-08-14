---
name: feedback-no-auto-gas-commit
description: GAS 專案的 commit/push 由使用者自行執行，不得自動進行
metadata: 
  node_type: memory
  type: feedback
  originSessionId: bb56d029-9560-415e-b6b5-81b4aa353174
---

GAS 專案（`D:\Git\SNShien\gas_live_integration`）的 commit 和 push 由使用者自行執行，不得自動觸發。

**Why:** 使用者明確要求自己控制 GAS 的版控流程。

**How to apply:** 修改 GAS 檔案後，只需告知檔案已修改完成，等使用者自行 commit/push 並部署。不得在沒有指示的情況下對 gas_live_integration 執行任何 git 操作。

此為 [[feedback_auto_commit_format]]（改完預設自動 commit 不 push）的例外：GAS 專案連 commit 也不自動做。
