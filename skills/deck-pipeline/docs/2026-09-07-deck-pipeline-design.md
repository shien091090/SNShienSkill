# deck-pipeline 設計規格

日期: 2026-09-07
狀態: 已實作並實跑一份簡報 (2026-09-08); 實作後的變更見 §11

## 1. 目的

一個可重複使用的 Claude Code skill, 把「一堆未整理的簡報素材」一路帶到「可編輯的 pptx」。
六個階段, 每階段都是人跟 AI 對話決策, 跨多次會話進行, 進度靠工作資料夾裡的狀態檔銜接。

不使用 LangGraph 或任何外部 orchestration 框架: 流程是線性六節點, 每節點都有 human gate, 狀態本質上就是資料夾本身。

## 2. 範圍

### 包含

- 單一 skill `deck-pipeline`, 位置 `~/.claude/skills/deck-pipeline/`, 與任何專案無關
- 觸發: 「做簡報」或 `/deck-pipeline <資料夾路徑>`; 不帶路徑就問
- 六階段: collect → organize → script → slides → style → build
- 素材新增/收集/拆分規則 (適用所有階段)
- SLIDES.md / STYLE.md / STATUS.md 格式規格
- `scripts/build_pptx.py`: 由 SLIDES.md + STYLE.md 生成可編輯 pptx
- 版型定案使用 Claude Code 的 `design` skill (canvas artboard)

### 不包含

- 照片、實機截圖: skill 只產 IMAGES_TODO.md 清單, 由使用者補; 畫得出來的圖 (示意圖 / 流程圖 / 比喻圖 / icon) 由 AI 寫 SVG, build 轉成原生圖案 (2026-09-08 變更, 見文末)
- 從 canvas 像素級複刻到 pptx: 只複刻版型規則, 不複刻微調細節
- 增量 build: 每次整份重建

## 3. 工作資料夾

輸入輸出同一個資料夾, 原地演化。使用者只給一個路徑。

```
<deck>/
  STATUS.md            進度 + topic 順序 + 每個 topic 狀態; 每次呼叫先讀
  (散檔)               階段 1: 截圖、txt、md 任意堆
  01_<topic>/          階段 2 後: 素材搬進來, 資料夾名前綴即順序
  02_<topic>/
  _unsorted/           討論後決定不用的素材, 不刪
  _archive/            被拆分過的原始檔, 不刪 (見 5.3)
  SCRIPT.md            階段 3: 完整講稿, 單一檔, 依 topic 分章節
  SLIDES.md            階段 4: 頁面內容, 單一檔, 依 topic 分章節
  IMAGES_TODO.md       階段 4 產出: 待補圖清單
  STYLE.md             階段 5: 定案版型規則
  output/<title>.pptx  階段 6 產出
```

決策紀錄:
- 素材搬移不複製 (使用者要求), 唯一例外是拆分過的原檔進 `_archive/`
- 講稿與頁面內容各自單一檔放根目錄, 不逐 topic 分檔 (使用者要能一眼檢閱整份)
- topic 子資料夾只放素材

## 4. 六階段

每階段定義: 進入條件 / 做什麼 / 完成條件。

### 4.1 collect (堆素材)

- 進入: 資料夾存在
- 做: 建立 STATUS.md, `stage: collect`。素材由使用者自行堆放
- 完成: 使用者說堆好了
- 存在意義: 讓 STATUS.md 從第一天就在

### 4.2 organize (分 topic)

- 進入: stage = collect 且使用者說堆好了
- 做:
  1. 讀全部散檔 (截圖用 Read 看圖, 文字檔讀內容)
  2. 提出 topic 切分與順序, 附每份素材的歸屬建議
  3. 使用者反覆調整到滿意
  4. 定案後: 建子資料夾、搬檔、拆分 (見 5.3)、更新 STATUS.md topic 表
- 完成: 根目錄除 STATUS.md 外沒有散檔; `_archive/` 每個檔都能對到至少一個拆分後的檔

### 4.3 script (講稿)

- 進入: organize 完成
- 做: 逐 topic 寫 SCRIPT.md。每個 topic 寫完停下給使用者看, 回饋修改後才往下一個 topic
- 內容: 演講重點條列 (一個 topic 3~6 條, 每條一句), 可帶「這邊要放某張截圖」註記; 是講者備忘稿密度, 不是長文, 也不是要放上簡報的字 (2026-09-07 實跑後由使用者修正, 原設計為長文)
- 開寫前先問聽眾、時長、標題; 自己補的觀點標 `[待確認]`
- 完成: 每個 topic 在 STATUS.md 標 `script: done`

### 4.4 slides (頁面內容)

- 進入: script 完成
- 做: 從 SCRIPT.md 出發, 逐 topic 擬頁面, 寫入 SLIDES.md (格式見 6.2)。每頁只留最核心的字, 能用圖就用圖; 沒有現成圖的頁寫圖片描述並標 `TODO`。逐 topic 確認
- 完成時: 由 SLIDES.md 的 TODO 條目產生 IMAGES_TODO.md
- 完成: 每個 topic 標 `slides: done`

### 4.5 style (版型定案)

- 進入: slides 完成
- 做:
  1. 掃 SLIDES.md, 歸納出實際用到的版型集合 (初始字彙見 6.2)
  2. 呼叫 `design` skill 產一個 canvas, 每種用到的版型各 2~3 個 artboard 方案
  3. 使用者在 canvas 挑選與微調
  4. 把定案版型轉寫成 STYLE.md (格式見 6.3): 上半人讀描述, 下半 yaml 給腳本
- 完成: STYLE.md 存在且使用者確認
- 細節規則放 `references/stage-style.md`

### 4.6 build (生 pptx)

- 進入: style 完成
- 做: 跑 `scripts/build_pptx.py <deck資料夾>`, 產 `output/<title>.pptx`
- 可重跑: 改了 SLIDES.md 或 STYLE.md 就重 build
- 完成: pptx 產出且能開

### 4.7 每次呼叫的固定開場

1. 讀 STATUS.md (不存在則視為 collect 階段起點)
2. 回報: 「目前在 X 階段, Y 個 topic, 其中 Z 個講稿完成」
3. 問: 繼續當前階段, 還是回頭改前面的東西

### 4.8 回頭修改

允許回到任何前面階段。回頭改動後, 在 STATUS.md 對應 topic 的後續階段欄位標 `stale`, 提醒後續要重看。stale 不阻擋 build, 只是提醒。

### 4.9 互動原則

- 全部用純文字對話, 不用 AskUserQuestion 選單
- 逐 topic 確認, 不一次產完整份再問
- 提案先給結論與理由, 使用者拍板才動檔案

## 5. 素材規則 (適用所有階段)

原則: 所有素材都必須是資料夾裡的檔案, 不存在「只在對話裡講過」的素材。

### 5.1 請 AI 收集素材

用 WebSearch / WebFetch 找, 每份內容落成一個 md 檔, 檔頭記來源 URL 與抓取日期。網路圖片用 PowerShell 下載成檔案, 來源 URL 記進 STATUS.md log (圖片本身不能帶檔頭)。
落點: 已有對應 topic 就放該子資料夾, 否則放根目錄等分類。

### 5.2 對話補述

使用者在對話裡講的補充內容, 當場寫成 `note_<主題關鍵字>.md` 落檔。落點同上。

### 5.3 原素材拆分

一份文字檔內文跨多個 topic 時:
- 拆成多個檔, 命名 `<原檔名>__<topic關鍵字>.md`
- 每個拆分檔檔頭記「拆自: <原檔名>, 第 X~Y 段」
- 原檔搬進 `_archive/`, 不刪 (拆分可能切錯, 使用者回頭核對要看得到原文)

### 5.4 記錄

每次新增素材, 在 STATUS.md 該 topic 的備註欄記 `+素材 <日期> <檔名>`。

## 6. 檔案格式

完整規格放 `references/formats.md`, 這裡是定案要點。

### 6.1 STATUS.md

```
stage: slides            // collect | organize | script | slides | style | build
title: <簡報名稱>

| # | 資料夾 | script | slides | 備註 |
|---|---|---|---|---|
| 01 | 01_背景 | done | doing | +素材 2026-09-07 note_xxx.md |
| 02 | 02_做法 | done | - | |

log:
- 2026-09-07 organize 定案, 6 份素材, 1 份拆分
```

只記進度與事件, 不放內容。欄位值: `-` 未開始 / `doing` / `done` / `stale`。

### 6.2 SLIDES.md

- `#` 簡報名稱 (一個)
- `##` topic, 格式 `## 01 背景`, 與資料夾前綴對齊
- `###` 一頁, 標題前用方括號標版型: `### [text] 現況三個痛點`
- 不用 `---` 分頁; `###` 既可 parse 也能在預覽看出頁邊界
- 頁內容元素依版型:
  - 副標: 標題下第一行純文字 (title 版型)
  - 條列: `- ` 開頭 → body
  - 圖片: `![描述](路徑)`; 路徑填 `TODO` 即待補圖
  - 對比: markdown 表格, 兩欄 → left / right
  - `>` 引用區塊 → pptx speaker notes
- 版型初始字彙: `title` `section` `text` `image` `image-text` `compare`

範例:

```
# <簡報名稱>

## 01 背景

### [title] 為什麼要做這件事
副標一句

### [text] 現況三個痛點
- 痛點一
- 痛點二

### [image] 理想的樣子
![描述: 一張簡化的箭頭圖, 三步變一步](TODO)

### [compare] 舊 vs 新
| 舊 | 新 |
| 手動 | 自動 |

> 講稿對應: 第一段
```

### 6.3 IMAGES_TODO.md

由 SLIDES.md 的 `TODO` 圖片條目產生。每筆: 頁碼 (topic + 頁序)、描述、建議檔名 (含建議放置的 topic 資料夾)。圖補進資料夾後, 使用者或 AI 把 SLIDES.md 的 TODO 換成路徑, 重新產生此檔。

### 6.4 STYLE.md

上半: 人讀的版型描述 (配色意圖、字體、每種版型長什麼樣)。
下半: 一個 ```` ```yaml ```` 區塊給腳本吃:

```yaml
slide: {w: 13.333, h: 7.5}     # 16:9 英吋
theme:
  bg: "#FFFFFF"
  fg: "#1F2937"
  accent: "#2563EB"
  font_title: "Noto Sans TC"
  font_body: "Noto Sans TC"
layouts:
  text:
    - {role: title, box: [0.8, 0.6, 11.7, 1.2], size: 32, bold: true}
    - {role: body,  box: [0.8, 2.2, 11.7, 4.5], size: 20}
  image:
    - {role: title, box: [0.8, 0.5, 11.7, 1.0], size: 28}
    - {role: image, box: [0.8, 1.8, 11.7, 4.6]}
    - {role: body,  box: [0.8, 6.6, 11.7, 0.6], size: 16}
```

- 每個版型 = 一組元素; 元素 `role` 對應 SLIDES.md 欄位: `title` `subtitle` `body` `image` `left` `right`
- `box` = [x, y, w, h] 英吋
- 新增版型是改 yaml 不改程式
- 腳本只讀 yaml 區塊, 上半文字忽略

## 7. scripts/build_pptx.py

- 執行: `python build_pptx.py <deck資料夾>` (python 3.12 + python-pptx; 使用者機器預設 python 為 3.8 無 python-pptx, 用 RO 專案那顆 3.12 安裝)
- 輸入: `<deck>/SLIDES.md`、`<deck>/STYLE.md`、圖片路徑相對於 `<deck>/`
- 輸出: `<deck>/output/<title>.pptx`, title 取 SLIDES.md 的 `#`
- 行為:
  - 依頁版型查 STYLE.md layouts, 逐元素放置
  - 文字全部是真正的文字框 (可編輯)
  - 圖片按 box 等比縮放置中
  - `TODO` 圖: 灰底矩形, 中間印描述文字
  - `>` 引用寫進該頁 speaker notes
  - SLIDES.md 用到但 STYLE.md 沒定義的版型: 報錯列出, 不產出
  - 圖片路徑不存在 (非 TODO): 報錯列出, 不產出
- 每次整份重建
- `examples/mini-deck/` 為 smoke test 資料: 2 topic 5 頁, 含 STYLE.md 與一張 TODO 圖, 改腳本後跑一次確認能開

## 8. skill 佈局

```
~/.claude/skills/deck-pipeline/
  SKILL.md                開場步驟、六階段規則、素材規則、互動原則
  references/
    formats.md            STATUS / SLIDES / IMAGES_TODO / STYLE 完整格式
    stage-style.md        階段 5: 從 SLIDES.md 歸納版型、design skill 怎麼下、canvas 定案怎麼轉寫成 STYLE.md
  scripts/
    build_pptx.py
  examples/mini-deck/     最小範例, 驗腳本用
  docs/
    2026-09-07-deck-pipeline-design.md   本文件
```

SKILL.md 本體只放流程規則, 格式細節推到 references, 需要時才讀。

## 9. 錯誤處理

- STATUS.md 損壞或格式不符: 回報並問使用者是重建還是手修, 不自行猜
- stage 與資料夾實況打架 (例如 stage: organize 但根目錄已有 SLIDES.md): 回報差異, 以使用者裁決為準, 更新 STATUS.md
- design skill 不可用: 階段 5 退化為文字描述版型方案供使用者挑選, 直接寫 STYLE.md
- build 失敗: 列出全部錯誤 (缺版型、缺圖) 一次回報, 不逐個中斷

## 10. 驗證

- build_pptx.py 對 `examples/mini-deck/` 跑通, 產出 pptx 可用 PowerPoint 開啟, 文字可編輯, TODO 圖顯示灰框
- SKILL.md 走一次完整六階段 (用 mini-deck 或真實素材), 每階段開場回報與完成條件判斷正確
- 回頭修改路徑: 改 topic 順序後, 後續階段欄位正確標 stale

## 11. 實跑後變更 (2026-09-08, 第一份簡報「分組日榜AI協作開發心得」)

1. 講稿 (§4.3) 改為演講重點條列, 不是長文; 開寫前先問聽眾 / 時長 / 標題
2. 新增 `table` role: 三欄以上表格產真正的 pptx 表格
3. 新增 SVG 原生圖案: SLIDES.md 圖片路徑為 `.svg` 時, build 用 vendor 的 svg_to_pptx (MIT, 來自 ppt-master / typ2pptx) 轉成可編輯的 PowerPoint 圖案 group; 「畫得出來的圖」由 AI 寫 SVG, 只有照片 / 截圖留 TODO
4. 階段 5 (§4.5) 改為兩輪 canvas: 3 方向 × 3 代表頁選配色 → 選定方向 × 全部版型; 第二輪同時寫 STYLE.md 草稿並試 build
5. 階段 4 允許新增版型 (image2 / image-icons4 / table), 記 STATUS.md log
6. organize 提案以 3~5 個敘事層 topic 為底, 素材資料夾當步驟保留; 拆分提案逐段貼原文
7. build 錯誤處理補: pptx 開著的 PermissionError、STYLE.md 結構錯誤、格式錯的 `##` / `>`, 全部清楚回報不噴 traceback
8. 新增第七階段 polish (手動): build 產物由使用者送進桌面版 Claude Design 美化, 匯出放回 `output/<title>_final.pptx`, stage 改 done。CLI 的 `/design` 與 `/design-sync` 都接不到 claude.ai/design 的 pptx 匯入匯出 (查過官方文件), 所以這步不自動化; 美化後的小改在 `_final` 直接改並同步 SLIDES.md, 大改回 build 重跑再送一次
