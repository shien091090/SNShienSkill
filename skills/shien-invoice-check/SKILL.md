---
name: shien-invoice-check
description: 觸發詞「對帳」「重新比對」。使用者說「對帳 9月」「對帳 2026/09/01 2026/10/15」「對帳 {資料夾}」、補完記帳後說「重新比對」「再比一次」「刷新對帳報告」、要抓載具發票 / 雲端發票、下載財政部電子發票明細、查哪些發票漏記帳、核對 SNShien 記帳時使用。
---

# SNShien 發票對帳

以下 `{skill 目錄}` 指本 SKILL.md 所在目錄(載入 skill 時給的 base directory), 腳本都在這裡。

## 觸發詞：對帳

- 「對帳 {資料夾路徑}」→ 使用者已自備 CSV, 以該資料夾當資料資料夾, 跳到步驟 1
- 「對帳 {月份}」或「對帳 {起日} {迄日}」→ 先做步驟 0 自動下載, 再接步驟 1。只給月份就是該月 1 日到月底(或今天)
- 「重新比對」→ 見文末「觸發詞：重新比對」

除了步驟 0 要使用者輸入圖形驗證碼, 其餘**全程自動執行, 不需使用者確認**。每一步失敗就停下回報, 不往下做。

**資料資料夾**: 每個對帳區間一個資料夾 `%LOCALAPPDATA%\shien-invoice-check\data\{起日}_{迄日}`(日期寫 `YYYYMMDD`, 用使用者要求的區間, 例如 10 月是 `20261001_20261031`), 放下載的 CSV、比對結果 `result.json`、報告連結 `report_url.txt`。放在固定位置而不是 scratchpad, 是為了換對話後還能「重新比對」而不必重新登入。

### 0. 自動下載載具發票 CSV

`fetch_invoices.py` 會開 Edge 視窗, 依序登入每組已設定的手機條碼帳號, 每組由使用者輸入圖形驗證碼並按登入, 之後自動查詢、下載 CSV。跨月會自動拆成每月一次查詢(平台限制)。

**前置檢查**(缺什麼就停下來告訴使用者, 不要自己繞過):
- `python -c "import playwright"` 失敗 → `python -m pip install playwright`(用系統 Edge, 不需要 `playwright install`)
- 帳密存在 User 環境變數 `INVOICE_ACC{n}_PHONE` / `INVOICE_ACC{n}_PWD`, `n` 從 1 起連號, 腳本會用到第一個沒設定的編號為止。腳本自己讀登錄檔, 不必先檢查值; 一組都沒有時腳本會印出提示。**請使用者自己在 PowerShell 視窗設定, 不要叫他貼密碼進對話**——貼進來就會留在對話紀錄裡

**執行**(輸出到資料資料夾; 資料夾已存在時先刪掉裡面舊的 `*.csv`, 否則上次多出來的分頁檔會混進比對——CSV 隨時能重新下載, 刪了不可惜):

```bash
python "{skill 目錄}/fetch_invoices.py" --start 2026/09/01 --end 2026/09/30 --out "{資料資料夾}"
```

- 用 `run_in_background` 跑: 腳本會停在登入頁等驗證碼, 每組最多等 5 分鐘, 前景呼叫會逾時
- 啟動後馬上告訴使用者「Edge 已開, 帳密已填好, 請輸入驗證碼按登入; 一組下載完會換下一組, 每組都要輸入一次」
- 只重跑某幾組用 `--accounts 2`(逗號分隔)
- 輸出最後一行是「完成」才算全部成功; 「完成, 但帳號 N 未下載」→ 從前面的輸出找原因(登入逾時 / 環境變數未設定 / Edge 視窗已關閉 / 下載失敗), 告訴使用者是哪組、為什麼, 問要不要用 `--accounts` 重跑那幾組, 不要直接拿不完整的資料對帳
- 輸出資料夾裡出現 `acc{n}_error.png` → 讀截圖判斷網站狀態再回報
- 視窗被關掉時, 輸出中間可能夾著一段 Node.js 的 `TargetClosedError` 錯誤訊息, 那是 Playwright 驅動程式印的, 以最後一行為準; 已下載的 CSV 不受影響

**改這支腳本時不要記錄網路請求的 POST 內容**: 登入請求(`doLogin`)的 body 帶明文密碼, 印出來就會留在對話紀錄和 log 檔裡。

下載完成後接步驟 1。

### 1. 執行比對

```bash
python "{skill 目錄}/reconcile.py" --csv-dir "{資料資料夾}" --out "{資料資料夾}/result.json"
```

腳本負責: 讀資料夾內所有 CSV(依發票號碼合併明細、跨檔去重、略過淨額 ≤ 0)、從 `$SNSHIEN_ROOT\linebot_liveManagerIntegration\settings.py` 讀 GAS 網址、抓發票期間(含起始日前一天)的記帳、執行比對。比對規則與折扣商家清單寫在腳本開頭的說明與 `DISCOUNT_VENDORS`, 要調整規則就改腳本, 不要在對話裡手算。

- 輸出以「錯誤:」開頭 → 照訊息回報使用者並停止(找不到 CSV、`SNSHIEN_ROOT` 未設定、GAS 呼叫失敗等)
- 成功時印出摘要與可能漏記清單, 完整結果在 `--out` 的 JSON: `start`、`end`、`invoiceCount`、`missing[]`、`matched[]`; 每張發票有 `invoiceNo`、`date`、`storeName`、`netAmount`、`items[]`, `matched` 另有 `matchedBy`(`exact` / `subset` / `group`)、`discount`(`{rate, amount}` 或 null)、`records`, 同店合記(`group`)另有 `groupTotal`

### 2. 產生對帳報告並以 Artifact 連結呈現

```bash
python "{skill 目錄}/report.py" --result "{資料資料夾}/result.json" --out "{scratchpad}/對帳報告_{起日}_{迄日}.html"
```

版面與文字都由 `report.py` 產生, 要改報告樣式就改腳本, 不要手寫 HTML。HTML 只是發布用的暫存稿, 放 scratchpad 就好。輸出以「錯誤:」開頭 → 回報並停止。

發布(Artifact 工具, `description` 寫時間範圍與三個數字的摘要):
- 資料資料夾**沒有** `report_url.txt` → 新發布(`icon` 用 `receipt`), 把回傳的連結寫進 `report_url.txt`
- **有** `report_url.txt` → 更新同一個連結: 本對話還沒讀過或發布過它, 就先 `action: "read"` 那個網址, 再帶 `url` 發布; 不帶 `url` 會變成另一個新連結

最後在對話框中提供 Artifact 連結給使用者查看, 並列出可能漏記的摘要(幾筆、合計、金額較大的幾筆)。

## 觸發詞：重新比對

使用者補完記帳 Sheet 後, 想用已下載的發票再比一次。不重新登入下載。

1. 決定資料資料夾: 使用者有講月份或區間就用對應的資料夾; 沒講就用 `%LOCALAPPDATA%\shien-invoice-check\data` 下最近修改的那個, 並在回報裡說明用的是哪個區間。資料夾不存在或沒有 CSV → 告訴使用者要先「對帳 {月份}」下載。有 `result.json` 就先記下裡面 `missing` 的發票號碼, 重跑會覆蓋它
2. 照步驟 1、步驟 2 重跑(報告會更新到同一個連結)
3. 回報時對照第 1 步記下的清單: 可能漏記從幾筆變幾筆, 列出這次新比對到的發票
