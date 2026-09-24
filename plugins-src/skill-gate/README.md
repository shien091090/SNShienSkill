# skill-gate

請 Claude 下 `git commit` 時, 只要這次改動碰到 skill(含 SKILL.md 的資料夾), 會先被擋下: Claude 跑 skill 健檢(skill-audit), 列出可優化項目讓你勾選, 修完(或一項都不選)登記後才放行。

## 安裝

前置條件: 電腦有 Node.js(`node -v` 看得到版本)。

在 Claude Code 裡執行(從哪個目錄啟動都可以):

```
/plugin marketplace add https://git-it.yile808.com/bu01/game-platform-team/lobby-agent-client.git
/plugin install skill-gate@lobby-agent-client
```

私有 repo 沿用電腦上的 git 帳號設定, 能 clone lobby-agent-client 就能裝。裝完重開 Claude Code 生效。

- 更新: `/plugin marketplace update lobby-agent-client`, 或在 `/plugin` 介面開啟自動更新
- 移除: `/plugin uninstall skill-gate@lobby-agent-client`, 不會留下任何設定

## 擋不到的情況

- 自己在終端機或 GUI 工具 commit: 不經過 Claude, 不會被擋
- 關卡本身出錯時放行, 不卡 commit

## 健檢記錄

登記過的 skill 以內容指紋記在 plugin 的持久資料夾(`~/.claude/plugins/data/` 底下), 只存在本機。內容沒變就不會再擋; 換電腦後第一次 commit 會再檢查一次。

## 維護與發佈

正本在維護者的 `~/.claude/plugins-src/skill-gate/`, lobby-agent-client 的 `plugins/skill-gate/` 是發佈用的副本, 不要直接改副本。發佈步驟:

1. 在正本修改, 並把 `.claude-plugin/plugin.json` 的 `version` 往上加
2. 正本 commit
3. 把正本整個資料夾複製到 lobby-agent-client 的 `plugins/skill-gate/`, 但**不要帶 `.claude-plugin/marketplace.json`**(那是維護者本機市集用的; lobby-agent-client 的市集清單在 repo 根目錄的 `.claude-plugin/marketplace.json`)
4. lobby-agent-client commit、push
