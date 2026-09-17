# svg-trace 設計文件

日期: 2026-09-17
狀態: 已與使用者確認, 待產實作計畫

## 1. 目的

給一張圖 (截圖、別人簡報裡的示意圖、網路上的架構圖), 由 AI 用 SVG 重現它, 再轉成 PowerPoint 原生可編輯圖案, 輸出成 pptx。

**使用者拿到 pptx 之後要做的事是「當素材改」** — 進 PowerPoint 換文字、換配色、搬框線, 併進自己的簡報。這一點決定了整個設計的取捨方向: **追求結構正確與圖層乾淨, 不追求像素級相似**。

與 deck-pipeline 的關係: 兩者共用同一包 `svg_to_pptx` vendor code, 但功能與流程完全獨立, 互不依賴。deck-pipeline 是「一整份簡報的產線」, svg-trace 是「單張圖的臨摹工具」。

## 2. 範圍

### 接受的輸入

不限圖種。流程圖、架構圖、時序圖、心智圖、UI 截圖、資料圖表、照片、插畫都收。

但**開場必須做適合度分流**: AI 看過圖後先講一句評估再動手。

| 圖種 | 處理方式 |
| --- | --- |
| 向量感的圖 (流程圖、架構圖、示意圖) | 直接做, 這是主場 |
| UI 截圖 | 直接做, 但會簡化掉陰影與細部材質 |
| 資料圖表 | 建議走「讀出數據再重畫」而非臨摹, 但依使用者裁決 |
| 照片、複雜插畫 | 明確告知「SVG 重現效果會很差, 建議直接貼圖」 |

**分流是建議, 不是硬擋。** 使用者堅持要做就照做, 不再勸第二次。

### 刻意不做

- 不追求像素級相似。陰影、雜訊材質、手繪抖動一律抹平; 複雜漸層退成單色或兩段漸層
- 不做批次。一次一張圖, 理由是自我校正迴圈需要專注比對, 多張同跑會讓錯誤互相掩蓋
- 不繼承 deck-pipeline 的 STYLE.md 或任何版型設定。顏色一律照原圖取色
- 不做排版美化。輸出的 pptx 除了那個圖案以外全空白, 這是預期行為

## 3. 使用者流程

### 觸發

- `/svg-trace` — 明確指名
- 「描圖」 — 主要自然觸發詞
- 語意觸發: 「把這張圖變成可編輯的」「重畫成 PPT 圖案」「臨摹這張圖」

以上三種都寫進 SKILL.md 的 `description`。

### 帶圖的三種方式

1. **剪貼簿 (推薦)** — 使用者 `Win+Shift+S` 截圖後只打「描圖」。AI 呼叫 `svgtrace.py grab` 從剪貼簿撈影像存檔, 使用者完全不碰路徑
2. **檔案路徑** — 拖檔進終端機或直接打路徑
3. **貼進對話 (Ctrl+V)** — AI 看得到圖但檔案不在磁碟上。此時 AI **仍要順手跑一次 `grab`**: 使用者既然貼得出來, 圖多半還在剪貼簿裡, 撈到就升級成完整流程; 撈不到才退化成無 `palette`、無並排比對的目視模式

### 七個步驟

1. **取得圖檔** — 依上述三種方式之一, 確保磁碟上有檔案 (或確認進入目視退化模式)
2. **分流** — 看圖, 一句話講適合度評估
3. **取色** — 跑 `palette` 拿到真實 hex, 不憑印象猜色
4. **畫 SVG** — 依 `references/svg-rules.md` 的規則落檔
5. **自我校正迴圈, 上限 3 輪** — 跑 `render` 截圖 → AI 自行比對原圖 → 修正。每輪回報一句「這輪修了什麼」, 讓使用者看得出是在收斂還是原地打轉。提早收斂就提早結束, 不必跑滿 3 輪
6. **交件比對** — 跑 `render --against <原圖>` 產並排 PNG 給使用者看, 等使用者點名要改的地方。改到滿意為止
7. **出檔** — 跑 `build` 產 pptx

## 4. 產物與檔案佈局

### skill 本體

```
~/.claude/skills/svg-trace/
  SKILL.md
  docs/2026-09-17-svg-trace-design.md
  references/svg-rules.md
  scripts/svgtrace.py
  scripts/vendor/svg_to_pptx/
  scripts/tests/test_svgtrace.py
```

`scripts/vendor/svg_to_pptx/` 由 `deck-pipeline/scripts/vendor/svg_to_pptx/` 完整複製而來。兩邊的 `VENDOR.md` 都要加註「此檔另有一份在 <對方路徑>, 上游更新時一起更新」。

選擇複製而非共用的理由: skill 的價值在自我包含。使用者之後可能只想把 svg-trace 分給同事、或只同步一份到別台機器, 共用會在那時候壞掉。這包是凍結的 vendor code (VENDOR.md 註明無本地修改), 重複的實際維護成本接近零。

### 輸出產物

**有給圖片路徑時** — 產物放原圖旁邊:

```
<原檔名>.svg
<原檔名>.compare.png
<原檔名>.pptx
```

**走剪貼簿時** — 開工作資料夾:

```
~/svg-trace/<yyyymmdd-hhmmss>/
  source.png
  trace.svg
  compare.png
  trace.pptx
```

`.svg` 一定保留。理由是使用者之後要改時, 改 SVG 重 build 比在 PowerPoint 裡救快。

## 5. 腳本介面

單一入口 `scripts/svgtrace.py`, 四個子命令。

### grab

```
svgtrace.py grab [--out <png>]
```

內部呼叫 PowerShell 取剪貼簿影像存成 PNG。`--out` 省略時存進當次工作資料夾。

剪貼簿沒有影像時明確回報「剪貼簿沒有圖片」並非零退出, 不吐 traceback。

實作已驗證可行: `Get-Clipboard -Format Image` 取得影像後 `.Save($path, Png)`, 640x320 測試圖來回無損。

### palette

```
svgtrace.py palette <圖> [--n 12] [--at x,y ...]
```

輸出:

- 原圖像素尺寸
- PIL 量化出的前 N 個主色, 每個給 hex 與佔比
- `--at` 指定座標的精確取樣色

`--at` 存在的理由: 量化只回答「這張圖大致有哪些色」, 但「那條線是什麼藍」必須點名問。

### render

```
svgtrace.py render <svg> [--against <原圖>] [--out <png>]
```

用 Chrome headless 截圖, 視窗尺寸直接讀 SVG 的 viewBox。

`--against` 時用 PIL 把兩張等高並排, 中間留灰色分隔線, 上緣標 `ORIGINAL` / `TRACE`。標籤用 ASCII 而非中文, 避免踩 PIL 預設字型沒有中文字的問題。

找不到 Chrome 時報明確訊息並列出找過的路徑, 不靜默失敗。Chrome 路徑依序找: 環境變數 `CHROME`、`C:\Program Files\Google\Chrome\Application\chrome.exe`、`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` (Edge 同為 Chromium, `--headless --screenshot` 介面相同)。

### build

```
svgtrace.py build <svg> --out <pptx> [--name <圖案名>]
```

流程:

1. **驗證** — SVG 能否解析、有無轉換器不支援的元素。有問題就列出**全部**並非零退出, 不產半成品
2. **開檔或建檔** — `--out` 不存在時建 16:9 (13.333 x 7.5 吋) 空白檔; 存在時開檔**追加一頁**
3. **尺寸沿用** — 追加時沿用該檔既有的投影片尺寸, 不強制改成 16:9。使用者因此可以直接往自己的簡報裡追加而不破壞版面
4. **置入** — box 為投影片尺寸四邊各縮 0.5 吋, 圖案等比縮放置中
5. **存檔**

## 6. SVG 撰寫規則

細節寫進 `references/svg-rules.md`, 要點:

### viewBox 固定換算

viewBox 設成 `0 0 1184 <等比高>`, 其中 1184 = 12.333 吋 x 96。這樣 SVG 座標 1:1 對應 pptx 實際尺寸, 文字級數不會因縮放而跑掉。

原圖非 16:9 時以寬度為準等比推高度; 高度超出可用空間時改以高度為準回推寬度。

viewBox 的 1184 是以「新建 16:9 檔」的可用寬度為基準算出來的。追加進非 16:9 的既有簡報時, `build` 會依該檔實際 box 等比縮放, 文字級數隨之等比改變 — 這是預期行為, 不另外重算 viewBox。

### 支援的語法子集

轉換器 (`svg_to_pptx`) 支援: `rect` `circle` `ellipse` `line` `polyline` `polygon` `path` `text` `tspan` `g` `marker` (箭頭)、`stroke-dasharray` (虛線)、漸層。

不支援: `foreignObject`、濾鏡、外部圖片。`build` 的驗證階段會列出不支援元素。

### 分群慣例

用 `<g id="...">` 分群, 每群在 pptx 裡成為一個子群組。分群要照**語意**而非畫的順序 — 使用者是要進 PowerPoint 改, 群組分得有道理才好選取。

## 7. 錯誤處理

所有錯誤都要給人看得懂的訊息, 不吐 traceback:

| 情況 | 行為 |
| --- | --- |
| 剪貼簿沒有影像 | 回報並提示改用檔案路徑 |
| 找不到 Chrome | 列出找過的路徑 |
| SVG 解析失敗 | 報檔名與解析錯誤位置 |
| SVG 含不支援元素 | 一次列出全部, 非零退出 |
| pptx 被 PowerPoint 鎖住 | 捕捉 PermissionError, 回「請先關掉 PowerPoint 再重跑」 |
| 圖片路徑不存在 | 直接回報, 不猜測 |

## 8. 測試策略

走 TDD, 先寫測試。不依賴 Chrome 的部分佔多數, 可在任何機器上跑。

不需要 Chrome:

- viewBox 解析: 有 viewBox、沒有 viewBox 只有 width/height、width 帶單位三種
- 等比置中的數學: 寬受限與高受限兩種情況各驗一次
- 不支援元素偵測會回報且非零退出
- `--out` 不存在時建 16:9 檔
- `--out` 已存在時頁數加一, 且原有頁內容不變
- 追加進 4:3 檔案時沿用 4:3 尺寸, box 跟著變
- 同一份 pptx 追加兩次, shape id 不相撞
- `palette` 從合成的純色 PNG 取色, 結果正確
- `grab` 在剪貼簿無影像時的錯誤路徑

需要 Chrome (找不到時 skip, 不讓整包紅掉):

- `render` 能產出非空 PNG
- `render --against` 產出的並排圖寬度約為兩張之和

## 9. 相依與環境

```
py -3 -m pip install python-pptx
```

`python-pptx` 會一併帶進 `lxml` 與 `Pillow`。不需要 pyyaml (此 skill 沒有 STYLE.md)。另需 Chrome 或 Edge。

**SKILL.md 裡的指令一律寫 `py -3`, 不寫死版本號。** 這是 deck-pipeline 現在踩到的坑: 它寫死 `py -3.12-64`, 但機器上只有 3.14, 照著抄會直接失敗。

不需要 cairosvg、Inkscape、ImageMagick、LibreOffice。

## 10. 已驗證的技術假設

在設計階段實測過, 不是推測:

- Chrome headless 截 SVG 正常, 中文字、marker 箭頭、虛線都渲染得出來
- 同一份 pptx 連續追加兩次確實變成兩頁, 每頁一個 group
- `svg_to_pptx` 轉出的 group 在 pptx 裡是巢狀群組, 子元素各自獨立, 文字可選取
- PowerShell 剪貼簿取圖存檔來回無損
- deck-pipeline 既有的 39 個測試在 Python 3.14 + python-pptx 1.0.2 下全過, 表示 vendor code 在新版環境沒問題
