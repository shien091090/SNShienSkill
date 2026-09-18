# deck-pipeline 檔案格式

四個檔案都放在工作資料夾根目錄。腳本只讀 SLIDES.md 與 STYLE.md; STATUS.md 與 IMAGES_TODO.md 是給人與 AI 對話用的。

## STATUS.md

```
stage: slides            // collect | organize | script | slides | style | build | done
title: <簡報名稱>

| # | 資料夾 | script | slides | 備註 |
|---|---|---|---|---|
| 01 | 01_背景 | done | doing | +素材 2026-09-07 note_xxx.md |
| 02 | 02_做法 | done | - | |

log:
- 2026-09-07 organize 定案, 6 份素材, 1 份拆分
```

- `stage`: 目前所在階段; `done` = `output/<title>.pptx` 已確認無誤, skill 結束
- topic 表: 一行一個 topic, `#` 兩位數與資料夾前綴一致
- `script` / `slides` 欄位值: `-` 未開始 / `doing` / `done` / `stale` (前面階段被回頭改過, 這欄要重看)
- 備註: 新增素材記 `+素材 <日期> <檔名>`; 其他事件自由寫
- log: 一行一事件, 日期開頭, 新的加在最下面
- 只記進度與事件, 不放內容

## SLIDES.md

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
- 一句註解

### [compare] 舊 vs 新
| 舊 | 新 |
| 手動 | 自動 |

> 講稿對應: 第一段
```

結構規則:
- `# ` 簡報名稱, 只有一個, 缺少會報錯; 同時決定輸出檔名 `output/<簡報名稱>.pptx`
- `## <兩位數> <topic名>` 一個 topic, 必須跟資料夾 `<兩位數>_<topic名>` 對得起來; `## ` 必須是兩位數編號, 否則報錯
- `### [<版型>]` 一頁, **這行只放版型**; 缺方括號會報錯
- 頁標題寫在 `###` 的下一行, 獨立一行。開頭可加 `[章節標籤]` 前綴 (對應 role `label`, 通常放投影片左上角小字, 例如 `案例2` / `小結`)
- 標題之後的純文字行才是副標 (role `subtitle`)
- `### [<版型>] <頁標題>` 的舊寫法仍可 parse, 但沒有地方放 `label`, 新的頁一律用拆行寫法
- 不用 `---` 分頁

```
### [image]
[小結] 團隊擴大最明顯的變化就是出現了管理職
管理職不只是用來管人, 更是為了養那些取代了默契的東西
![意象: ... 呈現: ...](TODO)
```

頁內元素 (寫在 `###` 之後, 到下一個 `###` 或 `##` 為止):
- `- ` 開頭 → 條列, 對應 role `body`
- `![描述](路徑)` → 圖片, 對應 role `image`; 路徑相對於工作資料夾; 路徑填 `TODO` 即待補圖, 描述要寫清楚讓人能找圖或生圖
- `| a | b |` 表格列 → 對應 role `left` / `right`, 第一列是欄標題 (會加粗); `|---|` 分隔列可有可無
- `> ` 開頭 → speaker notes, 多行會合併; `>` 後面有沒有空格都可以
- `<!--` 開頭 → 註解行, 完全忽略。用來放頁碼、分隔線這類**只給人讀 SLIDES.md 用**的標記
- 其他純文字行 → 對應 role `subtitle`; 若版型沒有 `subtitle` 元素但有 `body` 且沒有條列, 會補進 `body`

頁碼標記慣例 (非必要, 但整份長簡報建議加):

```
<!-- ───── P04 ───── -->
### [text] 輪廓一: 小型團隊
```

頁碼是**整份簡報連續編號**, 不是 topic 內編號 — 下一個 topic 的第一頁接著上一個 topic 的最後一頁往下數。手寫的, 插頁刪頁後要自己重編。SLIDES.md 是「一眼看懂每頁實際呈現什麼」的文件, 配時、對應講稿第幾段、為什麼這樣切這類 meta **不要寫進來**, 寫 STATUS.md 的 log。

版型初始字彙與慣用元素:

| 版型 | 用途 | 通常含的 role |
|---|---|---|
| `title` | 全簡報開頭 | title, subtitle |
| `section` | 章節分隔 | title |
| `text` | 純文字重點 | title, body |
| `image` | 一張圖為主 | label, title, image, body (底部一行) |
| `image-text` | 左圖右文 | label, title, image, body |
| `compare` | 兩欄對比 | label, title, left, right |
| `image2` | 兩圖並排, 每欄可有小標 | label, title, left, right, image, image |
| `image4` | 左一大圖 + 右上一圖 + 右下兩小圖並排 | label, title, image ×4, subtitle |
| `table` | 三欄以上表格 | label, title, table, body (下方一行小結) |

`image2` 的欄小標用一列 markdown 表格給, 例如 `| 單頁大綱 | 短敘述 |` → 左欄 `單頁大綱`、右欄 `短敘述` (第一列自動加粗)。圖片則依序吃頁內的第 1、2、… 張。

版型可以新增, 只要 STYLE.md 有定義; 階段 4 依內容需要取名即可 (例如某份簡報的 `image-icons4` = 主圖 + 4 個圖示方塊)。

## IMAGES_TODO.md

由 `build_pptx.py <deck> --images-todo` 產生, 不手寫。

```
| 頁 | 描述 | 建議檔名 |
|---|---|---|
| 02_做法 第2頁 理想的樣子 | 描述: 一張簡化的箭頭圖 | 02_做法/p02_img1.png |
```

補圖流程: 圖放進建議路徑 → SLIDES.md 該行 `TODO` 改成路徑 → 重跑 `--images-todo` → 清單消掉那一筆。

建議檔名一律給 `.png`, 但示意圖 / 流程圖 / 比喻圖 / icon 這類「畫得出來」的圖應由 AI 寫 `.svg` (見 STYLE.md 一節的 SVG 規則), 不要留給使用者找; 只有照片、實機截圖才真的需要使用者補 `.png`。

## STYLE.md

上半自由文字, 給人讀 (配色意圖、字體選擇、每種版型長什麼樣、canvas 定案的 artboard 名稱)。腳本忽略。

下半一個 ```` ```yaml ```` 區塊, 腳本只讀這裡:

```yaml
slide: {w: 13.333, h: 7.5}       # 16:9 英吋
theme:
  bg: "#FFFFFF"                  # 背景
  fg: "#1F2937"                  # 預設文字色
  accent: "#2563EB"              # 強調色, 元素可用 color 覆寫
  font_title: "Noto Sans TC"
  font_body: "Noto Sans TC"
layouts:
  text:
    - {role: title, box: [0.8, 0.6, 11.7, 1.2], size: 32, bold: true}
    - {role: body,  box: [0.8, 2.2, 11.7, 4.5], size: 20}
  image:
    - {role: title, box: [0.8, 0.5, 11.7, 1.0], size: 28, bold: true}
    - {role: image, box: [0.8, 1.8, 11.7, 4.6]}
    - {role: body,  box: [0.8, 6.6, 11.7, 0.6], size: 16}
```

- `slide` / `theme` / `layouts` 三個 key 缺一報錯
- 每個版型 = 元素清單, 依序放置
- 元素欄位: `role` (必填) / `box` [x, y, w, h] 英吋 (必填) / `size` pt (文字類, 預設 18) / `bold` (預設 false) / `color` hex (預設 theme.fg)
- role 字彙: `title` `label` `subtitle` `body` `image` `left` `right` `table`; 其他值報錯
- `label` role: 頁標題行 `[xxx]` 前綴的章節標籤, 慣例放左上角、字級小於 title
- `table` role: 把該頁的 markdown 表格畫成真正的 pptx 表格 (可編輯), 欄數不限; 第一列是表頭, 加粗、底色 `header_bg` (預設 theme.accent)、字色 `header_fg` (預設 theme.bg); 其餘列底色 theme.bg; `left`/`right` 仍可用於兩欄對照
- 同一版型可放多個 `image` 元素, 依序吃該頁的第 1、2、... 張圖; 頁的圖比元素多的忽略, 比元素少的元素留空
- 圖片等比縮放置中放進 box; TODO 圖畫灰底 (#D1D5DB) 矩形加描述
- 圖片路徑以 `.svg` 結尾時不貼圖, 而是轉成一組 PowerPoint 原生圖案 (group), 等比縮放置中塞進 box, 群組內每個框/線/文字在 PowerPoint 裡都可個別編輯。用途: 示意圖、流程圖、icon 這類「沒有截圖、要畫」的圖, 由 AI 依 SLIDES.md 的描述寫 SVG 落檔
- SVG 撰寫規則: 根元素給 `viewBox="0 0 W H"`, W/H 用 box 英吋 × 96 (例如 box 寬 6.67 → 640px), 這樣文字大小在 pptx 裡才會跟版型一致; 顏色直接寫 STYLE.md theme 的 hex; 支援 rect/circle/ellipse/line/polyline/polygon/path/text/tspan/g/marker (箭頭)/stroke-dasharray (虛線)/漸層; 不支援 foreignObject、filter 以外的濾鏡、外部圖片, validate 會列出不支援元素; 用 `<g id="...">` 分群, 每群在 pptx 裡是一個子群組
- 轉換器: `scripts/vendor/svg_to_pptx/` (MIT, 來自 ppt-master / typ2pptx)
- 從 canvas 轉寫尺寸: canvas artboard 1280x720 px 時, 英吋 = px / 96
