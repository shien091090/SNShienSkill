# dashboard

輸入框上方的綜合儀表板:

- 目前模型, 旁邊的 `▾` 可展開選單快速切換模型(等同打 `/model`)
- session 名稱、usage 血條與 token 用量
- 有連 Unity MCP 時顯示目前開著的 Unity 專案
- 「Todo」按鈕: 讀寫 `~/.claude/TODO.md` 的個人待辦(一筆一行 `- [ ] 內容 (YYYY-MM-DD)`)
- 回應完成時跳出 Windows 通知

## 安裝

在 Claude Code 裡執行(從哪個目錄啟動都可以):

```
/plugin marketplace add https://git-it.yile808.com/bu01/game-platform-team/lobby-agent-client.git#develop
/plugin install dashboard@lobby-agent-client
```

網址結尾的 `#develop` 不能省: repo 的預設分支是 main, 省略的話會抓 main, 找不到市集清單而加入失敗。已經加過這個市集(例如裝過 skill-gate)就只要跑第二行。裝完重開 Claude Code 生效。

- 更新: `/plugin marketplace update lobby-agent-client`, 或在 `/plugin` 介面開啟自動更新
- 移除: `/plugin uninstall dashboard@lobby-agent-client`

## 維護與發佈

正本在維護者的 `~/.claude/skills/dashboard/`, lobby-agent-client 的 `plugins/dashboard/` 是發佈用的副本, 不要直接改副本。發佈步驟:

1. 在正本修改, 跑 `claude plugin test ~/.claude/skills/dashboard`, 並把 `.claude-plugin/plugin.json` 的 `version` 往上加
2. 正本 commit
3. 把正本整個資料夾複製到 lobby-agent-client 的 `plugins/dashboard/`
4. lobby-agent-client commit、push
