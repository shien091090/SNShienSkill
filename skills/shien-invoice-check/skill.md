---
description: 比對財政部發票 CSV 與 SNShien 記帳紀錄，找出漏記的發票
---

# SNShien 發票對帳

## 觸發詞：對帳

當使用者說「對帳 {資料夾路徑}」時，執行以下步驟（**全程自動執行，不需使用者確認**）：

### 1. 掃描資料夾中所有 CSV 檔案

使用 PowerShell 列出資料夾中所有 CSV：

```powershell
Get-ChildItem "{資料夾路徑}" -Filter "*.csv" | Select-Object -ExpandProperty FullName
```

若清單為空，告知使用者「資料夾中找不到 CSV 檔案」並停止。

列出所有 `.csv` 路徑後，使用 Read 工具逐一讀取每個檔案。

### 2. 解析發票資料

對每個 CSV 檔案，依以下規則解析：

- **跳過**：第一行（標題）以及任何第一欄不是 `手機條碼` 的行（頁尾說明）
- **欄位索引**（0-based，逗號分隔）：
  - 欄 1：發票日期（格式 `YYYYMMDD`）
  - 欄 2：發票號碼
  - 欄 7：賣方名稱
  - 欄 12：消費明細_金額（數字，可為負）
- **按發票號碼分組**，計算每張發票淨額 = 所有同號碼行的欄 12 加總（含負數折扣）
- **略過**淨額 ≤ 0 的發票
- **去重**：若同一發票號碼已從其他 CSV 讀到，略過重複的
- **日期格式轉換**：`YYYYMMDD` → `YYYY/MM/DD`（例如 `20260620` → `2026/06/20`）

整理成發票清單，每筆包含：`{ invoiceNo, date (yyyy/MM/dd), storeName, netAmount }`

### 3. 讀取 GAS API URL

讀取 `D:\Git\SNShien\linebot_liveManagerIntegration\settings.py`，找到 `URL_GAS_API = '...'` 這行，取出單引號內的 URL。

若找不到該行，告知使用者「無法從 settings.py 讀取 URL_GAS_API」並停止。

### 4. 呼叫 GAS API 取得記帳資料

日期範圍 = 發票清單中最早的 date 至最晚的 date。

```powershell
$startDate = "yyyy/MM/dd"   # 最早發票日期（從發票清單取得）
$endDate   = "yyyy/MM/dd"   # 最晚發票日期（從發票清單取得）
$gasUrl    = "..."           # 從 settings.py 讀到的 URL_GAS_API
$uri = "${gasUrl}?action=action_get_accounting_items&startDate=$startDate&endDate=$endDate"
$r = Invoke-WebRequest -Uri $uri -UseBasicParsing -MaximumRedirection 5 -TimeoutSec 15
$r.Content
```

解析回傳 JSON，得到記帳紀錄清單，每筆：`{ date (yyyy/MM/dd), content, prize (integer), budgetType }`

### 5. 執行逐發票 Subset Sum 比對

#### 固定折扣商家清單（DISCOUNT_VENDORS）

以下商家與店主有固定折扣協議，比對時須同時嘗試原金額與折扣後金額：

| 賣方名稱（完整或部分符合） | 折扣率 |
|---|---|
| 新知喬股份有限公司 | 95折（× 0.95） |

**折扣金額計算**：`discountedAmount = Math.round(netAmount × 折扣率)`

#### 比對流程（兩段式 ± 1 日）

對**每一天**有發票的日子，依以下步驟處理：

**候選記帳池**：從全域剩餘池中取出 `date == D-1 OR date == D` 的記帳項目（已匹配的項目已從全域池移除，不重複使用）。

**Pass 1 — 單筆精確匹配（優先）**：
對所有候選發票（任意順序），在候選池中尋找：
- 若發票屬於折扣商家：同時嘗試 `netAmount` 與 `discountedAmount` 作為目標
- 若找到單筆記帳項目金額恰好等於目標金額 → 匹配成功，將該記帳項目從候選池移除

**Pass 2 — Subset Sum 補配**：
對 Pass 1 未匹配的發票，依 `netAmount` **由大到小**排序後依序處理：
- 若發票屬於折扣商家：先嘗試以 `netAmount` 做 subset sum；若失敗，再嘗試以 `discountedAmount` 做 subset sum
- 找到 → 移除命中的記帳項目，標記為 `matched`（若用折扣金額匹配成功，備註說明折扣）
- 找不到 → 標記為 `missing`

Subset sum backtracking 演算法概念：
```
findSubset(pool, target, startIndex, current):
  if sum(current) == target → return current        # 找到
  if startIndex >= len(pool) or sum(current) > target → return null
  withItem = findSubset(pool, target, startIndex+1, current + [pool[startIndex]])
  if withItem != null → return withItem
  return findSubset(pool, target, startIndex+1, current)
```

### 6. 產生本機 HTML 報表並開啟瀏覽器

使用 Write 工具將 HTML 寫入以下路徑（檔名包含日期範圍）：

```
C:\Users\lithoshu\Desktop\對帳報告_{startDate}_{endDate}.html
```

例如：`對帳報告_20260601_20260629.html`

HTML 必須是完整的獨立網頁（`<!DOCTYPE html>` 開頭、`<html><head><body>` 完整結構、所有 CSS 內嵌於 `<style>`，不依賴任何外部資源）。

**HTML 報表內容規格：**

頂部 Header（深玉綠色背景 `#2B7A58`，白字）：
- 小標：`SNShien · 發票對帳`
- 主標：`對帳報告`
- 副標：時間範圍，例如 `2026/06/01 – 2026/06/29`
- 三個統計 chip：
  - `發票總數 N`（半透明白底）
  - `已比對 N`（綠色背景 `#DCF0E5`，綠字）
  - `可能漏記 N`（橘色背景 `#FBE9DF`，橘字）

Table 1 — 可能漏記（左側橘紅色 4px border，橘色 header 背景）：
- 欄位：日期 | 賣方名稱 | 發票號碼 | 淨額 | 備註
- 可展開品項明細（點選列展開）
- 若無漏記，顯示「🎉 所有發票皆已對到帳，無漏記！」

Table 2 — 已比對（`<details><summary>` 預設收合，灰色）：
- 欄位：日期 | 賣方名稱 | 發票號碼 | 淨額
- 若該發票是透過折扣金額匹配成功，於淨額欄後加灰色小字，例如：`$444` `（95折後 $422 已入帳）`

頁尾說明文字：比對邏輯（兩段式 ± 1 日）：①先找當日∪前一日記帳中單筆精確匹配；②其餘以 exact subset sum 補配。折扣商家（如新知喬95折）會同時嘗試原金額與折扣後金額。金額無法對齊時標記為可能漏記，請人工確認。

寫入完成後，用 PowerShell 開啟檔案：

```powershell
Start-Process "C:\Users\lithoshu\Desktop\對帳報告_{startDate}_{endDate}.html"
```

最後告知使用者報告已開啟，並列出可能漏記的摘要（幾筆、哪幾天）。
