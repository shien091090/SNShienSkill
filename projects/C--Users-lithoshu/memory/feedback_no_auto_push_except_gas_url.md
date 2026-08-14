---
name: feedback-no-auto-push-except-gas-url
description: linebot 專案除更新GAS API URL以外，commit 和 push 都由使用者自行操作
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ce004394-4bb3-4691-8944-030dbc4e74ca
---

linebot_liveManagerIntegration 專案中，除了「更新GAS網址」skill 觸發詞明確授權的流程以外，不要自動執行 git add、git commit 或 git push（包含 heroku push）。

**Why:** 使用者希望自己控制 commit 和 push 時機。

**How to apply:** 修改程式碼後直接停止，不做任何 git 操作。「更新GAS網址」skill 是唯一例外（skill 本身已包含完整授權）。gas_live_integration 的 git 操作同樣由使用者自行執行（見 [[feedback_no_auto_gas_commit]]）。

此為 [[feedback_auto_commit_format]]（改完預設自動 commit 不 push）的例外：linebot 專案連 commit 也不自動做。

See also: [[feedback_no_auto_gas_commit]]
