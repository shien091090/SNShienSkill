---
description: 切換到 808 Lobby 專案目錄並載入 Slot_Lobby 程式碼規範
---

# Lobby 專案環境設定

執行以下步驟，完整設定 Lobby 開發環境：

## Step 1 — 切換工作目錄

使用 PowerShell 將工作目錄切換至專案根目錄：

```powershell
Set-Location D:\Git\808_Lobby_6000\Slot_Lobby
```

執行後確認目前位於 `D:\Git\808_Lobby_6000\Slot_Lobby`。

## Step 2 — 載入程式碼規範

讀取主規範檔案：

- `D:\Git\808_Lobby_6000\aiToolLib\.claude\CLAUDE.md`

CLAUDE.md 內含完整的 rules 對應表與目錄位置。讀取後，若使用者的任務涉及特定功能，依照 CLAUDE.md 內的說明，從 `D:\Git\808_Lobby_6000\aiToolLib\.claude\rules\` 目錄按需載入對應的規則檔案。

## Step 3 — 載入 Skill 索引

讀取以下檔案，載入可用的 Skill 清單：

- `D:\Git\lobby-agent-client\SKILLS.md`

讀取後記住各 Skill 的觸發詞，當使用者的指令符合時，讀取對應的 SKILL.md 並執行。

## Step 4 — 載入企劃規格目錄

使用 PowerShell 列出 `D:\Git\spec-lobby` 底下的所有**子資料夾名稱**：

```powershell
Get-ChildItem -Path D:\Git\spec-lobby -Directory | Select-Object -ExpandProperty Name
```

**僅記憶子資料夾名稱清單，不讀取任何 md 文件內容（省 Token）。**

此資料夾為企劃規格存放處。當使用者想查找某份規格時，從已記憶的資料夾名稱中定位目標，再讀取該資料夾內的 md 文件。

---

## Step 5 — 確認設定完成

完成後向使用者回覆：

```
已切換至 Lobby 專案：D:\Git\808_Lobby_6000\Slot_Lobby
程式碼規範已載入（Slot Lobby — Claude Code 開發規範）
```

接著等待使用者的具體任務指示。
