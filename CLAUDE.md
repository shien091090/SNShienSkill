# CLAUDE.md

全域使用者指示。位於 `~/.claude/CLAUDE.md`, 每個 session 都會載入, 且隨這個 repo 同步到所有裝置。細則拆在 `~/.claude/rules/`, 這裡只放指標。

## Memory 政策

auto-memory 只記一種東西: **進行中、跨 session 要接、且不是在建置 skill 的工作**(`project_*.md`, 必帶 `done_when`)。使用者糾正、路徑、偏好一律不進 memory, 該去 rule 或 skill。做完即刪, 不等提醒。完整規則與 skill 汙染清查流程見 `~/.claude/rules/memory-policy.md`。

## Commit 規範

任何 repo 要下 commit 之前, 先讀 `~/.claude/rules/commit-format.md` 全文再動手, 格式、submodule 處理、專案別例外都在那份。
