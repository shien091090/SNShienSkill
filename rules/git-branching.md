# 開分支規則

從遠端分支開新分支時**一律加 `--no-track`**: `git checkout --no-track -b feature/x origin/master`, 開完馬上 `git branch -vv` 確認 upstream 是空的, 第一次 push 用 `git push -u origin feature/x` 讓它追蹤自己的遠端分支。任何 commit 前跑 `git config --get branch.<name>.merge`, 值不是 `refs/heads/<name>` 就 `git branch --unset-upstream`。

**Why:** 2026-09-14 在 mr_server 用 `git checkout -b feature/lobby-autofix origin/master` 開分支, upstream 被自動設成 `origin/master`; 使用者在 GUI 工具按 push, 5 次 push 全部推進共用的 origin/master(18 個 commit), 遠端根本沒有 feature 分支, local master 也跟著跑。不能假設「我沒下 push 就不會被推」, 使用者會用 GUI push 當前分支, 推去哪完全看 upstream。
