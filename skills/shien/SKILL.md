---
description: 切換到 SNShien 專案目錄並準備開發環境
---

# SNShien 專案環境設定

執行以下步驟，設定 SNShien 開發環境：

## 專案結構說明

專案根目錄 `D:\Git\SNShien` 包含以下兩個子專案：

- **`linebot_liveManagerIntegration`**：主要 Python/LINE Bot 後端，部署於 Heroku
- **`gas_live_integration`**：Google Apps Script 程式碼，透過 clasp 管理

---

## Step 1 — 切換工作目錄並讀取專案

使用 PowerShell 將工作目錄切換至專案根目錄：

```powershell
Set-Location D:\Git\SNShien
```

執行後確認目前位於 `D:\Git\SNShien`。

接著讀取兩個子專案的主要檔案，建立對專案內容的基本認識：

```powershell
Get-ChildItem "D:\Git\SNShien\linebot_liveManagerIntegration" -Recurse -File | Select-Object FullName
Get-ChildItem "D:\Git\SNShien\gas_live_integration" -Recurse -File | Select-Object FullName
```

---

## Step 2 — 檢查 GAS pre-push hook

使用 PowerShell 檢查 `gas_live_integration` 的 pre-push hook 是否存在：

```powershell
Test-Path "D:\Git\SNShien\gas_live_integration\.git\hooks\pre-push"
```

若回傳 `False`，自動建立：

```powershell
$hookContent = "#!/bin/sh`nclasp push"
Set-Content -Path "D:\Git\SNShien\gas_live_integration\.git\hooks\pre-push" -Value $hookContent -NoNewline
```

建立後告知使用者「已建立 pre-push hook」；若已存在則不需提及。

---

## 專案參考資源

- **Google Sheet（資料來源）**：https://docs.google.com/spreadsheets/d/1vDFl5qpQb_oTj0xZt1PRw-39yvfbvsYZx04BN10ZQHQ/edit?usp=sharing

---

## 觸發詞：更新GAS網址

當使用者說「更新GAS網址: {url}」或貼上新的 GAS 部署網址時，執行以下步驟（**全程自動執行，不需使用者確認**）：

### 1. 更新 settings.py

修改 `D:\Git\SNShien\linebot_liveManagerIntegration\settings.py` 中的 `URL_GAS_API`：

```python
URL_GAS_API = '{新網址}'
```

### 2. Commit + Push（GitHub + Heroku）

```powershell
Set-Location "D:\Git\SNShien\linebot_liveManagerIntegration"
git add settings.py
$dt = Get-Date -Format "yyyy/MM/dd HH:mm"
git commit -m "更新GAS API URL($dt)`n`nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push
git push heroku main
```

若 `heroku` remote 不存在，先執行：
```powershell
heroku git:remote -a linebot-livemanagerintegration
```

### 3. 驗證新網址

用 PowerShell 確認新 URL 可正常回傳 JSON（非 HTML 錯誤頁）：

```powershell
$r = Invoke-WebRequest -Uri "{新網址}?action=action_memo_get" -UseBasicParsing -MaximumRedirection 5 -TimeoutSec 15
$r.Content.Substring(0, [Math]::Min(200, $r.Content.Length))
```

若開頭是 `{` 代表成功；若是 `<!DOCTYPE` 代表 GAS 仍有授權問題。

完成後告知使用者結果。

---

## 觸發詞：gas pull

當使用者說「gas pull」時，執行以下步驟：

### 1. 從 GAS 拉取最新程式碼

```powershell
Set-Location "D:\Git\SNShien\gas_live_integration"
clasp pull
```

### 2. 比對檔案差異

```powershell
git -C "D:\Git\SNShien\gas_live_integration" diff --name-only 2>$null
```

若有變動檔案，逐一查看 diff 內容：

```powershell
git -C "D:\Git\SNShien\gas_live_integration" diff {檔名} 2>$null | Out-File -FilePath "$env:TEMP\gas_diff.txt" -Encoding utf8
Get-Content "$env:TEMP\gas_diff.txt"
```

### 3. 回報結果

將變動摘要告知使用者（哪些檔案有改動、改了什麼）。不詢問是否需要 commit，直接結束。

---

## 觸發詞：部屬Heroku

當使用者說「部屬Heroku」時，執行以下步驟：

### 1. 確認 heroku remote

```powershell
git -C "D:\Git\SNShien\linebot_liveManagerIntegration" remote -v
```

若清單中沒有 `heroku`，先加入：
```powershell
Set-Location "D:\Git\SNShien\linebot_liveManagerIntegration"
heroku git:remote -a linebot-livemanagerintegration
```

### 2. Push 到 Heroku

```powershell
git -C "D:\Git\SNShien\linebot_liveManagerIntegration" push heroku main
```

### 3. 確認部署版本

部署完成後，從輸出中找到 `Released vXXX` 告知使用者版本號。

---

## Step 3 — 確認設定完成

完成後向使用者回覆：

```
已切換至 SNShien 專案：D:\Git\SNShien
```

接著等待使用者的具體任務指示。
