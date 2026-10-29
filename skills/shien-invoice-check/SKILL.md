---
name: shien-invoice-check
description: 觸發詞「對帳」。使用者說「對帳 9月」「對帳 2026/09/01 2026/10/15」「對帳 {資料夾}」、要抓載具發票 / 雲端發票、下載財政部電子發票明細、查哪些發票漏記帳、核對 SNShien 記帳時使用。
---

# SNShien 發票對帳

以下 `{skill 目錄}` 指本 SKILL.md 所在目錄(載入 skill 時給的 base directory), 腳本都在這裡。

## 觸發詞：對帳

- 「對帳 {資料夾路徑}」→ 使用者已自備 CSV, 跳到步驟 1
- 「對帳 {月份}」或「對帳 {起日} {迄日}」→ 先做步驟 0 自動下載, 再接步驟 1。只給月份就是該月 1 日到月底(或今天)

除了步驟 0 要使用者輸入圖形驗證碼, 其餘**全程自動執行, 不需使用者確認**。每一步失敗就停下回報, 不往下做。

### 0. 自動下載載具發票 CSV

`fetch_invoices.py` 會開 Edge 視窗, 依序登入每組已設定的手機條碼帳號, 每組由使用者輸入圖形驗證碼並按登入, 之後自動查詢、下載 CSV。跨月會自動拆成每月一次查詢(平台限制)。

**前置檢查**(缺什麼就停下來告訴使用者, 不要自己繞過):
- `python -c "import playwright"` 失敗 → `python -m pip install playwright`(用系統 Edge, 不需要 `playwright install`)
- 帳密存在 User 環境變數 `INVOICE_ACC{n}_PHONE` / `INVOICE_ACC{n}_PWD`, `n` 從 1 起連號, 腳本會用到第一個沒設定的編號為止。腳本自己讀登錄檔, 不必先檢查值; 一組都沒有時腳本會印出提示。**請使用者自己在 PowerShell 視窗設定, 不要叫他貼密碼進對話**——貼進來就會留在對話紀錄裡

**執行**(輸出資料夾放 scratchpad 下新建的空資料夾, 例如 `{scratchpad}\invoice_20260901_20260930`):

```bash
python "{skill 目錄}/fetch_invoices.py" --start 2026/09/01 --end 2026/09/30 --out "{輸出資料夾}"
```

- 用 `run_in_background` 跑: 腳本會停在登入頁等驗證碼, 每組最多等 5 分鐘, 前景呼叫會逾時
- 啟動後馬上告訴使用者「Edge 已開, 帳密已填好, 請輸入驗證碼按登入; 一組下載完會換下一組, 每組都要輸入一次」
- 只重跑某幾組用 `--accounts 2`(逗號分隔)
- 輸出最後一行是「完成」才算全部成功; 「完成, 但帳號 N 未下載」→ 告訴使用者是哪組、原因(逾時 / 環境變數未設定), 問要不要重跑那組, 不要直接拿不完整的資料對帳
- 輸出資料夾裡出現 `acc{n}_error.png` → 讀截圖判斷網站狀態再回報
- 最後若有一段「BrowserContext.close: Connection closed」的錯誤, 是使用者提早關掉 Edge 視窗, 已下載的 CSV 不受影響

**改這支腳本時不要記錄網路請求的 POST 內容**: 登入請求(`doLogin`)的 body 帶明文密碼, 印出來就會留在對話紀錄和 log 檔裡。

下載完成後, 以輸出資料夾當作 CSV 資料夾接步驟 1。

### 1. 執行比對

```bash
python "{skill 目錄}/reconcile.py" --csv-dir "{CSV 資料夾}" --out "{scratchpad}/對帳結果_{起日}_{迄日}.json"
```

腳本負責: 讀資料夾內所有 CSV(依發票號碼合併明細、跨檔去重、略過淨額 ≤ 0)、從 `$SNSHIEN_ROOT\linebot_liveManagerIntegration\settings.py` 讀 GAS 網址、抓發票期間(含起始日前一天)的記帳、執行比對。比對規則與折扣商家清單寫在腳本開頭的說明與 `DISCOUNT_VENDORS`, 要調整規則就改腳本, 不要在對話裡手算。

- 輸出以「錯誤:」開頭 → 照訊息回報使用者並停止(找不到 CSV、`SNSHIEN_ROOT` 未設定、GAS 呼叫失敗等)
- 成功時印出摘要與可能漏記清單, 完整結果在 `--out` 的 JSON: `start`、`end`、`invoiceCount`、`missing[]`、`matched[]`; 每張發票有 `invoiceNo`、`date`、`storeName`、`netAmount`、`items[]`, `matched` 另有 `matchedBy`、`discount`(`{rate, amount}` 或 null)、`records`

### 2. 產生對帳報告並以 Artifact 連結呈現

讀步驟 1 的 JSON 產生報告。發布前先 load `artifact-design` skill 校準設計投入程度。

將 HTML 寫入 scratchpad 目錄下的暫存檔(檔名包含日期範圍, 例如 `對帳報告_20260601_20260629.html`), 不要存到 Desktop 或任何使用者可見的持久路徑——這份檔案只是發布用的暫存稿。

**HTML 報表內容規格：**

頂部 Header(深玉綠色背景 `#2B7A58`, 白字):
- 小標: `SNShien · 發票對帳`
- 主標: `對帳報告`
- 副標: 時間範圍(`start` – `end`), 例如 `2026/06/01 – 2026/06/29`
- 三個統計 chip:
  - `發票總數 N`(半透明白底)
  - `已比對 N`(綠色背景 `#DCF0E5`, 綠字)
  - `可能漏記 N`(橘色背景 `#FBE9DF`, 橘字)

Table 1 — 可能漏記(左側橘紅色 4px border, 橘色 header 背景):
- 欄位: 日期 | 賣方名稱 | 發票號碼 | 淨額 | 備註
- 可展開品項明細(點選列展開, 內容取 `items`)
- 若無漏記, 顯示「🎉 所有發票皆已對到帳，無漏記！」

Table 2 — 已比對(`<details><summary>` 預設收合, 灰色):
- 欄位: 日期 | 賣方名稱 | 發票號碼 | 淨額
- `discount` 不是 null 時, 於淨額欄後加灰色小字, 例如: `$444` `（95折後 $422 已入帳）`

頁尾說明文字: 比對邏輯(兩段式 ± 1 日): ①先找當日∪前一日記帳中單筆精確匹配; ②其餘以 exact subset sum 補配。折扣商家(如新知喬95折)會同時嘗試原金額與折扣後金額。金額無法對齊時標記為可能漏記, 請人工確認。

寫入完成後, 用 Artifact 工具發布(`icon` 用 `receipt`, `title` 用「對帳報告」, `description` 為時間範圍摘要)。

最後在對話框中提供 Artifact 連結給使用者查看, 並列出可能漏記的摘要(幾筆、哪幾天)。
