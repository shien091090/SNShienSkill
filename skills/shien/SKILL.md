---
description: 切換到 SNShien 專案目錄並準備開發環境
---

# SNShien 專案環境設定

執行以下步驟，設定 SNShien 開發環境：

## 專案結構說明

專案根目錄（路徑因裝置而異，見 Step 0）包含以下兩個子專案：

- **`linebot_liveManagerIntegration`**：主要 Python/LINE Bot 後端，部署於 Heroku
- **`gas_live_integration`**：Google Apps Script 程式碼，透過 clasp 管理

---

## Step 0 — 確認專案路徑（環境變數）

專案根目錄不寫死在 skill 裡，改用使用者層級環境變數 `SNSHIEN_ROOT` 存放，讓同一份 skill 能在不同裝置上指向不同路徑。

### 1. 讀取環境變數並驗證

```powershell
$env:SNSHIEN_ROOT
if ($env:SNSHIEN_ROOT) { Test-Path $env:SNSHIEN_ROOT }
```

- 有輸出路徑且 `Test-Path` 為 `True` → 路徑有效，跳到「2. 確認子專案存在」。
- 沒有輸出（未設定）或 `Test-Path` 為 `False` → 詢問使用者「這台裝置上 SNShien 專案根目錄的實際路徑是？」，取得路徑後寫入為 User 環境變數：

```powershell
[Environment]::SetEnvironmentVariable('SNSHIEN_ROOT', '{使用者提供的路徑}', 'User')
$env:SNSHIEN_ROOT = '{使用者提供的路徑}'
```

寫入 User 層級後，這台裝置之後開的新 PowerShell / Claude session 會自動讀到這個值，不需要重問。

### 2. 確認子專案存在

```powershell
Test-Path "$env:SNSHIEN_ROOT\linebot_liveManagerIntegration"
Test-Path "$env:SNSHIEN_ROOT\gas_live_integration"
```

若任一個回傳 `False`，直接告知使用者哪個子專案在 `$env:SNSHIEN_ROOT` 底下找不到，不要自行猜測或搜尋其他路徑。

---

## Step 1 — 切換工作目錄並讀取專案

使用 PowerShell 將工作目錄切換至專案根目錄：

```powershell
Set-Location $env:SNSHIEN_ROOT
```

執行後確認目前位於 `$env:SNSHIEN_ROOT` 所指的路徑。

接著讀取兩個子專案的主要檔案，建立對專案內容的基本認識：

```powershell
Get-ChildItem "$env:SNSHIEN_ROOT\linebot_liveManagerIntegration" -Recurse -File | Select-Object FullName
Get-ChildItem "$env:SNSHIEN_ROOT\gas_live_integration" -Recurse -File | Select-Object FullName
```

---

## Step 2 — 確認 GAS 部署環境（clasp）

`gas_live_integration` 透過 clasp 部署到 Google Apps Script。全新裝置上需要三件事都到位：clasp 已安裝、已登入授權、`.clasp.json` 已連結到正確的 GAS 專案。`.clasp.json` 被 `.gitignore` 排除、不會隨 git clone 帶過來，每台新裝置都要重建一次。

### 1. 確認 clasp 已安裝

```powershell
Get-Command clasp -ErrorAction SilentlyContinue
```

沒找到就安裝：

```powershell
npm install -g @google/clasp
```

### 2. 確認 `.clasp.json` 已連結專案

```powershell
Test-Path "$env:SNSHIEN_ROOT\gas_live_integration\.clasp.json"
```

若回傳 `False`，建立它（scriptId 是這個 GAS 專案固定的值，不會因裝置而變）：

```powershell
$claspConfig = @{ scriptId = '1bPOXP0XfEU-OiFgvm4sahG106lxB6Er1D9orG-Jau5Kp4y_LRkTuEgnV'; rootDir = '.' } | ConvertTo-Json
Set-Content -Path "$env:SNSHIEN_ROOT\gas_live_integration\.clasp.json" -Value $claspConfig
```

### 3. 確認已登入 clasp

```powershell
Set-Location "$env:SNSHIEN_ROOT\gas_live_integration"
clasp status
```

若出現登入/授權相關錯誤，代表這台裝置還沒登入過——**這是互動式 OAuth，Claude 沒辦法代為操作**，請使用者自己在提示字元前加 `!` 執行，並停在這裡等使用者回報登入完成，不要自行嘗試繞過：

```
! clasp login
```

### 4. 檢查 pre-push hook

```powershell
Test-Path "$env:SNSHIEN_ROOT\gas_live_integration\.git\hooks\pre-push"
Get-Content "$env:SNSHIEN_ROOT\gas_live_integration\.git\hooks\pre-push" -Raw -ErrorAction SilentlyContinue
```

正確內容應該是（`deploymentId` 是正式環境固定值，不會因裝置而變）：

```
#!/bin/sh
clasp push --force && clasp deploy -i AKfycbydY2IAQ2CLCeU2baHfdWO1rCCzZPOUp8qt_fS2967yZYkmcn7b1Q-zOk2kixYV36dNXQ
```

若檔案不存在，或內容跟上面不一致（例如舊版只有 `clasp push`，或只有 `clasp push --force` 但沒有後面的 `clasp deploy`），(重新)建立：

```powershell
$hookContent = "#!/bin/sh`nclasp push --force && clasp deploy -i AKfycbydY2IAQ2CLCeU2baHfdWO1rCCzZPOUp8qt_fS2967yZYkmcn7b1Q-zOk2kixYV36dNXQ"
Set-Content -Path "$env:SNSHIEN_ROOT\gas_live_integration\.git\hooks\pre-push" -Value $hookContent -NoNewline
```

**為什麼兩步都要**：
- **`--force`**：clasp 只要偵測到 `appsscript.json`（manifest）跟遠端有一點點差異（哪怕只是行尾符號），沒加 `--force` 就會直接印出「Skipping push.」但不報錯——`git push` 表面上成功，GAS 其實完全沒有部署到新版。這個坑已經實測踩過。
- **`clasp deploy -i <deploymentId>`**：`clasp push` 只會更新 Apps Script 專案的 HEAD（開發版）內容，**不會**讓正式的 `/exec` 網址自動跟著換版本——那個網址是綁定在特定 deployment 的固定版本號上。這個坑也已經實測踩過：曾經連續好幾次 `clasp push` 都成功，但正式環境（LINE bot、家庭總覽 dashboard 實際呼叫的網址）一直停在舊版本沒更新，導致程式邏輯跟已經改過格式的 Google Sheet 對不上、算出全部歸零。用同一個 `deploymentId` 重新 `clasp deploy` 才會讓 `/exec` 網址真正切到最新程式碼，網址本身不會變。

建立/修正後告知使用者「已建立（或已修正）pre-push hook」；若已經正確則不需提及。

---

## 專案參考資源

- **Google Sheet（資料來源）**：https://docs.google.com/spreadsheets/d/1vDFl5qpQb_oTj0xZt1PRw-39yvfbvsYZx04BN10ZQHQ/edit?usp=sharing

---

## 觸發詞：更新GAS網址

當使用者說「更新GAS網址: {url}」或貼上新的 GAS 部署網址時，執行以下步驟（**全程自動執行，不需使用者確認**）：

### 1. 更新 settings.py

修改 `$env:SNSHIEN_ROOT\linebot_liveManagerIntegration\settings.py` 中的 `URL_GAS_API`：

```python
URL_GAS_API = '{新網址}'
```

### 2. Commit + Push（GitHub + Heroku）

```powershell
Set-Location "$env:SNSHIEN_ROOT\linebot_liveManagerIntegration"
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
Set-Location "$env:SNSHIEN_ROOT\gas_live_integration"
clasp pull
```

### 2. 比對檔案差異

```powershell
git -C "$env:SNSHIEN_ROOT\gas_live_integration" diff --name-only 2>$null
```

若有變動檔案，逐一查看 diff 內容：

```powershell
git -C "$env:SNSHIEN_ROOT\gas_live_integration" diff {檔名} 2>$null | Out-File -FilePath "$env:TEMP\gas_diff.txt" -Encoding utf8
Get-Content "$env:TEMP\gas_diff.txt"
```

### 3. 回報結果

將變動摘要告知使用者（哪些檔案有改動、改了什麼）。不詢問是否需要 commit，直接結束。

---

## 觸發詞：部屬Heroku

當使用者說「部屬Heroku」時，執行以下步驟：

### 1. 確認 heroku remote

```powershell
git -C "$env:SNSHIEN_ROOT\linebot_liveManagerIntegration" remote -v
```

若清單中沒有 `heroku`，先加入：
```powershell
Set-Location "$env:SNSHIEN_ROOT\linebot_liveManagerIntegration"
heroku git:remote -a linebot-livemanagerintegration
```

### 2. Push 到 Heroku

```powershell
git -C "$env:SNSHIEN_ROOT\linebot_liveManagerIntegration" push heroku main
```

### 3. 確認部署版本

部署完成後，從輸出中找到 `Released vXXX` 告知使用者版本號。

---

## Step 3 — 確認設定完成

完成後向使用者回覆（將 `{路徑}` 換成 `$env:SNSHIEN_ROOT` 實際的值）：

```
已切換至 SNShien 專案：{路徑}
```

接著等待使用者的具體任務指示。
