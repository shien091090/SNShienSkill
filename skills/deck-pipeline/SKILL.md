---
name: deck-pipeline
description: 觸發詞「做簡報」或 /deck-pipeline <資料夾路徑>。把一個堆滿簡報素材 (截圖、txt、md) 的資料夾, 經六個階段 (堆素材 → 分 topic → 講稿 → 頁面內容 → 版型定案 → 生 pptx) 帶到可編輯 pptx。跨多次會話進行, 進度靠資料夾內 STATUS.md 銜接。使用者提到要做簡報、整理簡報素材、寫講稿、把講稿變投影片、或指向一個已有 STATUS.md 的資料夾時使用。
---

# deck-pipeline

一個資料夾, 六個階段, 使用者拍板、AI 動手, 到 `output/<title>.pptx` 為止。排版美化不在這個 skill 範圍內, 由使用者自行處理 (例如手動送桌面版 Claude Design)。輸入輸出都在同一個資料夾原地演化, 與任何專案無關。

格式規格在 `references/formats.md`, 階段 5 細節在 `references/stage-style.md`, 需要時才讀。

## 每次呼叫的固定開場

1. 拿到資料夾路徑 (參數沒帶就問)。資料夾不存在就停下來問
2. 讀 `STATUS.md`。不存在 → 視為 collect 起點, 建立它。格式損壞 → 回報, 問使用者重建還是手修, 不自行猜
3. 比對 stage 與資料夾實況 (例如 stage: organize 但根目錄已有 SLIDES.md)。有打架 → 回報差異, 以使用者裁決為準更新 STATUS.md
4. 回報一句: 「目前在 X 階段, Y 個 topic, 其中 Z 個講稿完成」
5. 問: 繼續當前階段, 還是回頭改前面的東西

## 互動原則

- 全部純文字對話, 不用 AskUserQuestion 選單
- 逐 topic 確認, 不一次產完整份再問
- 提案先給結論與理由, 使用者拍板才動檔案
- 所有素材必須是資料夾裡的檔案, 不存在「只在對話裡講過」的素材 (見「素材規則」)

## 資料夾樣貌

```
<deck>/
  STATUS.md            進度與 topic 表
  (散檔)               階段 1 堆放區
  01_<topic>/          階段 2 後: 素材搬進來, 前綴即順序
  _unsorted/           決定不用的素材, 不刪
  _archive/            被拆分過的原始檔, 不刪
  SCRIPT.md            講稿, 單一檔
  SLIDES.md            頁面內容, 單一檔
  IMAGES_TODO.md       待補圖清單 (腳本產生)
  STYLE.md             版型規則
  output/<title>.pptx        階段 6 build 產物, 即最終交付
```

## 六階段

### 1. collect 堆素材

- 做: 建立 STATUS.md (`stage: collect`)。素材由使用者自行堆放, AI 不動
- 完成: 使用者說堆好了 → stage 改 organize

### 2. organize 分 topic

- 讀全部散檔: 截圖用 Read 看圖, 文字檔讀內容。檔案多就用 subagent 平行讀回摘要
- 提出 topic 切分與順序, 附每份素材的歸屬建議, 標出需要拆分的檔
- topic = 講述段落, 不等於素材資料夾。使用者的素材常已按主題預分好資料夾, 提案以 3~5 個敘事層 topic 為底 (例如: 以往怎麼做 / 這次怎麼做 / 流程展開 / 痛點與下一步), 既有資料夾當 topic 底下的步驟保留, 加 `N_` 前綴排序; 不要一個資料夾一個 topic
- 提拆分方案時逐段貼出每一份拆分後的原文, 不寫「第 N~N 行」, 使用者看不出內容
- 不要為了 parser 改資料夾名 (路徑帶括號、空白都能 parse); 改名只在使用者要求或要加排序前綴時做
- 使用者反覆調整到滿意才動檔
- 定案後: 建 `01_<topic>/` 子資料夾、搬檔 (不複製)、拆分 (見素材規則)、不用的進 `_unsorted/`、寫 STATUS.md topic 表
- 完成: 根目錄除 STATUS.md 與流程檔 (SCRIPT.md / SLIDES.md / IMAGES_TODO.md / STYLE.md) 外沒有散檔; `_archive/` 每個檔都對得到至少一個拆分檔 → stage 改 script

### 3. script 講稿

- 逐 topic 寫 `SCRIPT.md`, 每個 topic 一個 `## 01 <topic>` 章節
- 內容是演講重點條列, 密度是「講者在備忘稿上一眼看懂接下來要講什麼」: 一個 topic 3~6 條, 每條一句, 可帶「這邊放 xxx.png」註記。不寫長文、不鋪陳、不寫講稿逐字稿。不是要放上投影片的字, 但也不是文章
- 開寫前先問聽眾是誰、時長、簡報標題, 記進 SCRIPT.md 檔頭與 STATUS.md title
- 自己補的觀點 (原素材沒有的) 標 `[待確認]`, 由使用者決定留不留
- 每個 topic 寫完停下給使用者看, 回饋修改後才往下一個; STATUS.md 該 topic `script` 欄 doing → done
- 完成: 全部 topic `script: done` → stage 改 slides

### 4. slides 頁面內容

- 從 SCRIPT.md 出發, 逐 topic 擬頁面寫進 `SLIDES.md`, 格式見 `references/formats.md`
- 每頁只留最核心的字, 能用圖就用圖。有現成截圖就填路徑, 沒有就寫圖片描述、路徑填 `TODO`, 描述要具體到能拿去找圖或生圖
- 沒有截圖但「畫得出來」的圖 (架構示意、流程圖、比喻圖、icon 方塊) 不要留 TODO 給使用者找圖: 由 AI 依描述寫成 `.svg` 落在該 topic 資料夾, 路徑填進 SLIDES.md, build 時會轉成可編輯的 PowerPoint 原生圖案。SVG 撰寫規則見 `references/formats.md`。真的需要照片/實機截圖的才留 TODO
- 用 `> ` 註記對應講稿段落, 會進 speaker notes
- 版型可以在這階段新增: 內容需要現有六種以外的排法 (兩圖並排、主圖加多個圖示、三欄以上表格) 就直接取名用 (`image2` / `image-icons4` / `table` 這類), 記進 STATUS.md log, 階段 5 照清單出方案
- 逐 topic 確認; STATUS.md 該 topic `slides` 欄 doing → done
- 全部完成後跑 `py -3.12-64 ~/.claude/skills/deck-pipeline/scripts/build_pptx.py <deck> --images-todo` 產 IMAGES_TODO.md, 告知使用者哪些圖要補。補圖不在 skill 範圍, 沒補的圖 build 時會是灰框
- 完成: 全部 topic `slides: done` → stage 改 style

### 5. style 版型定案

照 `references/stage-style.md` 做。摘要: 歸納 SLIDES.md 用到的版型 → 問風格方向 → design skill 出 canvas (每版型 2~3 方案) → 使用者挑選微調 → 轉寫 STYLE.md → 使用者確認 → stage 改 build。

### 6. build 生 pptx

```
py -3.12-64 ~/.claude/skills/deck-pipeline/scripts/build_pptx.py <deck>
```

- 成功: `output/<title>.pptx`, 文字皆可編輯, TODO 圖為灰框加描述, `>` 進 notes
- 失敗: 腳本列出全部錯誤 (版型未定義 / 圖片不存在), 修 SLIDES.md 或 STYLE.md 後重跑
- 改了 SLIDES.md 或 STYLE.md 就重 build, 每次整份重建
- 相依: `py -3.12-64 -m pip install python-pptx pyyaml` (SVG 轉換器已 vendor 在 scripts/vendor, 不用另裝)
- pptx 正在 PowerPoint 裡開著會 build 失敗 (PermissionError), 先請使用者關掉再重跑
- STYLE.md 用到的字型播放機器要裝, 沒裝 PowerPoint 會退系統字; 定案時提醒使用者
- 完成: 使用者確認內容無誤 (字、圖、頁序) → stage 改 done。skill 到此結束, 排版美化由使用者自行處理

## 素材規則 (所有階段適用)

任何時候新增素材都走同一套: 落檔 → 歸 topic → STATUS.md 該 topic 備註記 `+素材 <日期> <檔名>`。還沒有 topic 就放根目錄等分類。

- **使用者請 AI 收集**: WebSearch / WebFetch 找, 每份內容一個 md 檔, 檔頭記來源 URL 與抓取日期。網路圖片用 PowerShell 下載成檔案, 來源 URL 記進 STATUS.md log
- **對話補述**: 使用者在對話裡講的補充, 當場寫成 `note_<主題關鍵字>.md`
- **拆分**: 一份文字檔內文跨多個 topic 時, 拆成 `<原檔名>__<topic關鍵字>.md`, 每個拆分檔檔頭記「拆自: <原檔名>, 第 X~Y 段」; 原檔搬進 `_archive/` 不刪

## 回頭修改

允許回到任何前面階段。改動後, 在 STATUS.md 對應 topic 的後續階段欄位標 `stale`, 提醒要重看。stale 不阻擋 build。

改 topic 順序或改 topic 名稱時的檢查清單, 一項一項確認:
- 資料夾改名 (`NN_<topic>`)
- SLIDES.md 的 `## NN <topic>` 與該 topic 下所有圖片路徑
- SCRIPT.md 章節標題
- STATUS.md topic 表
- 後續階段欄位標 `stale`
- 重跑 `--images-todo`

## 錯誤處理

- STATUS.md 損壞: 問使用者, 不自行重建
- stage 與資料夾實況打架: 回報, 使用者裁決
- design skill 不可用: 階段 5 退化為文字描述方案 (見 stage-style.md 第 6 節)
- build 失敗: 一次列全部錯誤, 不逐個中斷
