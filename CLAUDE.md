# CLAUDE.md

全域使用者指示。位於 `~/.claude/CLAUDE.md`，每個 session 都會載入，且隨這個 repo 同步到所有裝置。

## Skill 開發期間不要寫 auto-memory

在 `~/.claude/skills/` 底下開發、調整或測試任何 skill 時（包含只是跟使用者討論該 skill 的行為），過程中學到的**踩坑經驗、環境限制、必要步驟、失敗模式**一律寫進該 skill 的 `SKILL.md`，不要寫進 auto-memory。

**Why:** auto-memory 存在 `~/.claude/projects/<cwd-key>/memory/`，被 gitignore 且綁定工作目錄，只有這台機器的這個目錄讀得到；skill 則跟著 git 走到每台機器。知識若落進 memory 會造成兩個問題：一是換機器跑同一個 skill 時那份知識不存在，坑會重踩；二是測試當下我同時讀得到 memory 和 skill，跑起來很順，但驗證的其實是「skill + 這台機器的 memory」而不是 skill 本身——等於考題外流的測試，使用者會誤以為 skill 已經完備。

**How to apply:** 判準不是「這是不是使用者偏好」，而是**「這份知識有沒有跟著 git 走」**：

- skill 執行時需要用到的 → 寫進該 skill 的 `SKILL.md`
- 跨專案的環境事實與通則 → 寫進這份 `CLAUDE.md`（或日後拆到 `~/.claude/rules/`）
- 只有特定工作目錄才成立的專案狀態（路徑、未解待辦、該專案的慣例） → 才留給 auto-memory

需要完全隔離時：`/pause-memory` 暫停單一 session，或 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 直接斷掉讀寫兩邊。

## 輸出 skill 穩定版本前要做汙染清查

撰寫或修改 skill 時，中間無論經歷多少輪討論與調整，在**輸出一個穩定版本**（宣告 skill 寫好、可以使用，或要 commit）之前，必須回頭做一次 memory 與 skill 的汙染清查：

1. 讀過所有 auto-memory 目錄（`~/.claude/projects/*/memory/`），找出與這個 skill 相關的內容
2. 逐條判斷：skill 執行需要的 → 補進 `SKILL.md`；跨專案通則 → 提到這份 `CLAUDE.md`
3. 搬完之後**刪除**該 skill 相關的 memory 檔案與 `MEMORY.md` 索引行，不要留重複的一份
4. 向使用者回報搬了什麼、刪了什麼

**Why:** 中途的討論會不斷產生 memory，而「skill 是否完備」無法靠「我跑起來很順」判斷——我很可能正在靠 memory 補洞而不自知。清查是唯一能確認 skill 自給自足的方法。

**How to apply:** 這一步不可省略，也不要等使用者提醒。要再確認一層，就在一個沒用過的工作目錄下加 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 冷跑一次 skill，那等同模擬一台新機器。
