# Memory 政策

auto-memory(`~/.claude/projects/<cwd-key>/memory/`)被 gitignore 且綁工作目錄, 只有這台機器、這個目錄讀得到。判準永遠是: **這份知識有沒有跟著 git 走**。

## 一、只記一種東西: 進行中、跨 session 要接的工作

允許: `project_*.md`, 條件是工作做到一半、下個 session 要無縫接上, **且不是在建置 skill**。

其他一律不寫 memory, 改去它們該去的地方:
- 使用者糾正我的做法 → 跨專案通則進 `~/.claude/rules/`; skill 相關進該 SKILL.md; 專案專屬但屬個人偏好 → `~/.claude/rules/` 用 `paths:` frontmatter 限定生效目錄(專案 rules 是團隊共用, 不放個人偏好)
- 路徑、URL、工具位置 → 對應專案的 CLAUDE.md 或 spec; 純本機路徑放 `~/.claude/CLAUDE.md`
- 使用者偏好 → `~/.claude/CLAUDE.md` 或 output style
- 建置、調整、測試 skill 期間學到的任何東西(踩坑、環境限制、必要步驟、失敗模式)→ 該 skill 的 SKILL.md。落進 memory 的話, skill 跑起來順只是「skill + 本機 memory」的組合, 換機器就不如預期, 而且測試當下也看不出來

寫 memory 一律用 Write/Edit 工具, 不用 Bash 繞過——有 hook(`hooks/memory-guard.js`)在攔非 `project_*` 的寫入。

## 二、每份 memory 必帶 done_when

frontmatter 加 `done_when:`, 白話寫「什麼事發生這份就該刪」(例: M4 merge 進 main / spec 使用者 review 完 / 修法 commit)。寫不出來就不是進行中工作, 不寫。

## 三、完成即刪, 不等提醒

使用者表明某工作完成或棄置, 或 `done_when` 已達成(例如我剛 merge 了那個 branch)→ 當場刪 memory 與 MEMORY.md 索引行, 回報一句。

## 四、session 開頭的過期提醒

讀 MEMORY.md 時, 若有 memory 的 `modified` 超過 14 天, 在第一則回應末尾用一行提「N 份 memory 超過兩週沒動: X、Y, 還在進行嗎?」。只提一次, 使用者不回就不追。

## 五、清理範圍涵蓋所有 cwd

任何清理動作掃 `~/.claude/projects/*/memory/` 全部, 不只當前目錄。memory 綁 cwd, 換目錄開 session 就看不到舊的, 殘留多半躺在那。

## 六、skill 定案前的汙染清查

宣告 skill 寫好可以用、或要 commit 之前, 不可省略、不等使用者提醒:
1. 掃所有 memory 目錄, 找出與這個 skill 相關的內容
2. skill 執行需要的 → 補進 SKILL.md; 跨專案通則 → `~/.claude/rules/` 或 CLAUDE.md
3. 搬完刪除相關 memory 與索引行
4. 回報搬了什麼、刪了什麼

要再確認一層: 在沒用過的工作目錄下加 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 冷跑一次 skill, 等同模擬一台新機器。
