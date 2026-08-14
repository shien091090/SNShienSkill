---
description: 無獨立觸發詞，由 line-group-export skill 內部呼叫：讀取昨天所有 LINE 群組的聊天記錄，依 categories.json 規則用 AI 語意判斷是否有有用訊息並輸出統一摘要
---

# LINE 群組每日訊息摘要

## 說明

本 skill 沒有自己的使用者觸發詞，一律由 `line-group-export` skill（觸發詞「line日報」）內部呼叫執行，情境有二：使用者說「line日報」跑完整流程時，匯出結束後接續執行；或使用者說「line日報」並明確指示只要彙整時，跳過匯出直接執行本流程。

執行以下步驟（**全程自動執行，不需使用者確認**）：

### 1. 找出資料夾內所有匯出檔並切出昨天的訊息區塊

資料夾內可能同時有多個群組的匯出檔（每個 `.txt` 代表一個群組），全部都要處理。**必須用 PowerShell 7+（pwsh）執行**，確保 UTF-8 編碼正確比對中文日期標題（`$folder` 為固定監看資料夾）：

```powershell
function Get-DateLabel([datetime]$d) {
    $map = @('星期日','星期一','星期二','星期三','星期四','星期五','星期六')
    return "{0}.{1:D2}.{2:D2} {3}" -f $d.Year, $d.Month, $d.Day, $map[[int]$d.DayOfWeek]
}

$folder = "D:\倉庫\其他\Line社群訊息紀錄"
$files = Get-ChildItem -Path $folder -Filter "*.txt" -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\[LINE\]' }

if (-not $files -or $files.Count -eq 0) {
    Write-Output "NO_FILE_FOUND"
} else {
    $yesterday = (Get-Date).AddDays(-1).Date
    $startLabel = Get-DateLabel $yesterday
    $endLabel = Get-DateLabel $yesterday.AddDays(1)
    $anyFound = $false
    $blocks = @()

    foreach ($f in $files) {
        $allLines = [System.IO.File]::ReadAllLines($f.FullName, [System.Text.Encoding]::UTF8)
        $startIdx = [Array]::IndexOf($allLines, $startLabel)
        if ($startIdx -eq -1) {
            $blocks += "=== 群組: $($f.BaseName) — 昨天無資料 ==="
            continue
        }
        $anyFound = $true
        $endIdx = [Array]::IndexOf($allLines, $endLabel)
        $endBound = if ($endIdx -ne -1) { $endIdx - 1 } else { $allLines.Length - 1 }
        $blocks += "=== 群組: $($f.BaseName) ==="
        $blocks += ($allLines[($startIdx+1)..$endBound] -join "`n")
    }

    if (-not $anyFound) {
        Write-Output "ALL_NOT_FOUND:$startLabel"
    } else {
        $blocks -join "`n"
    }
}
```

**依輸出結果分流：**

- 若輸出為 `NO_FILE_FOUND`：告知使用者「在 `D:\倉庫\其他\Line社群訊息紀錄` 找不到任何 .txt 匯出檔，請確認路徑或先從 LINE 匯出聊天記錄」，流程中止。
- 若輸出**恰好是** `ALL_NOT_FOUND:` 開頭的單一字串（後面接的是日期字串，不含任何 `=== 群組:` 區塊）：告知使用者「所有匯出檔案中都找不到昨天（該日期）的紀錄，請重新從 LINE 匯出最新聊天記錄後再試一次」，流程中止。**不可**當作「無相關訊息」處理。
- 否則，輸出內容包含一個或多個 `=== 群組: XXX ===` 區塊（標示「— 昨天無資料」的區塊代表該群組跳過，其餘區塊後面接的是該群組昨天的原始訊息文字），進入下一步。

### 2. 讀取分類設定

用 Read 工具讀取 `C:\Users\lithoshu\.claude\skills\line-group-daily-report\categories.json`，取出所有 `enabled: true` 的分類（保留 `categories` 陣列原本順序），每個分類記住 `label` 與 `description`。

### 3. 過濾雜訊並用 AI 語意判斷分類

閱讀第 1 步取出的所有群組昨天訊息文字（略過標示「— 昨天無資料」的群組區塊），處理時：

**先略過以下雜訊，不當作候選訊息：**
- 以 `Auto-reply` 開頭的罐頭訊息，含其後續沒有時間戳記的延伸行（例如早安/午安/下班/晚安等固定公告，可能跨多行，直到下一則有 `HH:mm` 時間戳記開頭的訊息為止）
- 整行內容恰好是「`HH:mm 發言者 圖片`」「`HH:mm 發言者 影片`」「`HH:mm 發言者 貼圖`」的行（純媒體佔位、無其他文字說明）
- 系統訊息：「`OOO加入聊天`」「`OOO離開聊天`」

**對剩下的訊息，跨所有群組合併判斷**：依序對照第 2 步取出的每個分類的 `description`，用語意理解（不是關鍵字比對）判斷該訊息是否符合，不分訊息來自哪個群組。同一則訊息可以同時符合多個分類，各自收錄進對應分類。

### 4. 輸出摘要

- 依 `categories.json` 陣列原本順序，只輸出「有命中內容」的分類，段落標題用該分類的 `label`
- 每個分類下用 **Markdown 表格**呈現，固定兩欄：`資訊` / `來源群組`，一則命中訊息一列
  - `來源群組`欄位填該訊息所屬的群組名稱（來自 `=== 群組: XXX ===` 區塊，去掉開頭的 `[LINE]` 前綴）
  - `資訊`欄位內容：
    - **若該則屬於活動類訊息**（訊息在描述一個有具體時間、地點的活動/課程/特賣會等）：格式固定為 `{時間} {地點} {活動名稱或說明}`，三者之間用一個空格分隔，除此之外**不要**再附加報名費用、對象、聯絡方式、名額等其他細節。這裡的「時間」指活動本身的舉辦時間（從訊息內文擷取，例如「8/4(二) 09:00-16:00」），不是該則訊息在群組裡的發送時間戳記；「地點」用訊息中提到的地點名稱即可，不需完整地址。
    - **若該則不是活動類訊息**（例如新聞類）：維持原本簡潔的重點摘要寫法，不套用上述固定格式
  - 不附發言者、也不附訊息在聊天室裡的原始時間戳記（除非該時間戳記本身就是活動時間的一部分，見上）
- 若所有分類都沒有命中任何內容：只輸出一行「昨天無相關訊息」
- 輸出到目前對話框即可，不需要額外呼叫任何外部 API 或推播

### 5. 清空匯出資料夾

摘要輸出完成後（無論有沒有命中內容、也無論是走完整流程還是「只彙整」流程），刪除 `D:\倉庫\其他\Line社群訊息紀錄` 資料夾內所有檔名符合 `^\[LINE\]` 的 `.txt` 檔案（**全程自動執行，不需使用者確認**）：

```powershell
Get-ChildItem -Path "D:\倉庫\其他\Line社群訊息紀錄" -Filter "*.txt" -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\[LINE\]' } |
    Remove-Item -Force
```

**原因（2026-07-23 使用者指定採用）**：LINE「另存新檔」對話框如果偵測到目標路徑已有同名檔案會多跳出一個「是否覆蓋」確認彈窗，鎖定該彈窗的「是(Y)」按鈕座標常常要重試、拖慢整批匯出。摘要一旦讀取完成，這批 txt 檔案就沒有保留價值，清空後下次匯出時資料夾是空的，就不會再觸發覆蓋確認彈窗。若第 1 步輸出是 `NO_FILE_FOUND` 或 `ALL_NOT_FOUND:` 而中止流程，資料夾內本來就沒有本次要處理的檔案（或內容用不到），不需要執行這一步。
