# dashboard

輸入框上方的綜合儀表板:

- 目前模型, 旁邊的 `▾` 可展開選單快速切換模型(等同打 `/model`)
- session 名稱、usage 血條與 token 用量
- 有連 Unity MCP 時顯示目前開著的 Unity 專案
- 「Todo」按鈕: 讀寫 `~/.claude/TODO.md` 的個人待辦(一筆一行 `- [ ] 內容 (YYYY-MM-DD)`)
- 回應完成時跳出 Windows 通知
- (公司版)進測中的 Lobby 版本與送審日: 第一行是 master 的版本、送審日與剩幾天, 第二行是其他進測中的版本。版號用 `git ls-remote` 問 GitLab 上的 Lobby repo(要能連公司 GitLab), 送審日讀公開的送審日 Google Sheet, 只列表上有的版本; 每 30 分鐘更新一次

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

正本在維護者的 `~/.claude/plugins-src/dashboard/`, lobby-agent-client 的 `plugins/dashboard/` 是發佈用的副本, 不要直接改副本。

正本不放 `~/.claude/skills/`: 那裡的 plugin 會被自動載入, 而 `~/.claude` 同步到維護者每台電腦, 會變成每台都跑正本。放在 `plugins-src/` 不會自動載入, 由各台電腦自己決定:

- 公司電腦: 跟同事一樣照上面「安裝」用市集版, 不設環境變數
- 自家電腦: 不裝市集版, 用使用者環境變數 `CLAUDE_CODE_PLUGIN_DIRS` 直接載入正本(環境變數不跟 git 同步, 只有設的那台會載入)。設定一次, 在 PowerShell 跑完後關掉終端機重開:

  ```powershell
  [Environment]::SetEnvironmentVariable('CLAUDE_CODE_PLUGIN_DIRS', "$HOME\.claude\plugins-src\dashboard", 'User')
  ```

  之後 `~/.claude` git pull 就是最新版, 改檔存檔會自動重新載入。

發佈步驟:

1. 在正本修改, 跑 `claude plugin test ~/.claude/plugins-src/dashboard`, 並把 `.claude-plugin/plugin.json` 的 `version` 往上加
2. 正本 commit
3. 把正本整個資料夾複製到 lobby-agent-client 的 `plugins/dashboard/`
4. lobby-agent-client commit、push
