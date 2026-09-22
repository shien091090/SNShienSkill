# 階段 5 版型定案

目標: 從 SLIDES.md 歸納出要幾種版型, 用 design skill 出方案讓使用者挑, 把定案轉寫成 STYLE.md。
版型定一次整份沿用, 不逐頁調。

流程是兩輪 canvas: 第一輪選配色方向 (少量代表頁), 第二輪選定方向鋪滿全部版型。不要一次把「每種版型 × 多個方案」全丟出去, 20 幾張使用者看不完。

## 1. 歸納版型集合

掃 SLIDES.md 所有 `### [xxx]`, 列出用到的版型與頁數:

```
title 1 頁 / image-icons4 1 頁 / compare 1 頁 / image 2 頁 / image-text 3 頁 / image2 4 頁 / table 2 頁
```

只出有用到的版型 (含階段 4 新增的自訂版型, 看 STATUS.md log)。同時從每種版型挑一頁真實內容當 artboard 的填充文字 (不要用 lorem ipsum, 使用者要看得出實際長度合不合)。

## 2. 問使用者風格方向

一個問題, 純文字: 有沒有既定的配色/字體/品牌要求, 或參考的簡報風格。有就照著做, 第一輪只出 1 個方向 × 3 個代表頁讓使用者確認; 沒有就進第 3 步出 3 個方向讓使用者挑。

**字型預設用微軟正黑體 `Microsoft JhengHei`**, 不用問。pptx 只記字型名稱, 播放機器沒裝就會退成系統預設、版面跟著跑掉, 而微軟正黑體是 Windows 內建, 一定有。使用者主動指定別的才換。

canvas 上可以用網路字型看效果 (Google Fonts 之類), 但 STYLE.md 的 yaml 填微軟正黑體。兩者不同時在 STYLE.md 上半註明一句, 免得之後看 canvas 以為字型跑掉了。

## 3. 第一輪 canvas: 選配色方向

3 個方向 × 3 個代表版型 = 9 張 artboard。

- 3 個方向要真的不同 (例如: 白底單一強調色 / 深底亮字 / 米白暖色襯線標題), 不是同一風格的三個色階
- 3 個代表版型: 封面 (title) + 這份簡報用最多的多圖版型 + 表格或對比 (table / compare)
- artboard 尺寸 1280x720 (16:9, 之後 px/96 直接換算英吋)
- 每列一個方向, artboard title 標「A 白底藍強調 · 封面」這種, 方向名稱一旦定了不改
- 填充內容用第 1 步挑的真實頁面文字; 截圖位置用灰色虛線佔位塊, 塊內寫 SLIDES.md 的描述, 不放真圖
- 每個元素明確對應一個 role (title / subtitle / body / image / left / right / table), 元素不要多於 role 需要的數量; 裝飾性線條色塊可以有, 但要能用 theme 的 bg/accent 表達, 且要知道腳本不會畫它 (寫進 STYLE.md 上半當備註)
- canvas 上放一張 annotation 說明怎麼選

使用者選一列 (或說要混哪些元素) 才進第二輪。

## 4. 第二輪 canvas: 選定方向鋪滿

同一個 canvas 重發 (同一連結), 拔掉沒選的方向, 選定方向 × 全部用到的版型各一張, `Main.dc.html` 放封面。

發出的同時做兩件事, 不要等使用者回:
1. 依 artboard 的 px 值寫 STYLE.md 草稿 (換算規則見第 5 步), 檔頭標「草稿, 待 canvas 微調後對回」
2. 用草稿試 build 一次 pptx

然後請使用者兩邊一起看: canvas 上拖改版型, pptx 上看真截圖放進去的效果。實測使用者常直接定案, 省掉一輪往返。

## 5. 轉寫 STYLE.md

使用者有在 canvas 上改過就用 `Artifact read` 讀回, 找到被改的 artboard 對回; 沒改就把草稿標為定案。對每個元素:

- 位置尺寸 px → 英吋: 除以 96, 取到小數第二位
- 字級 px → pt: 乘 0.75, 取整
- 顏色取 hex; 跟 theme.fg 相同就不寫 `color`, 不同 (通常是強調色) 才寫
- 字重 ≥ 600 視為 bold
- 多圖版型 (image2 / image-icons4 這類) 每張圖一個 `image` 元素, 順序 = SLIDES.md 圖片順序
- 三欄以上表格用 `table` role, 表頭色寫 `header_bg` / `header_fg`

寫入 STYLE.md:
- 上半: 配色與字體說明、每種版型一句話描述、腳本不畫的裝飾備註、字型安裝提醒、選用的 artboard 名稱與 canvas URL
- 下半: yaml, 格式見 `formats.md`

## 6. 自己看一眼產出

canvas 發出去之前、SVG 畫完之後, 都該自己先看過 — 元素跑出畫面、文字溢出、線條交疊到看不懂這類問題, 不看圖是看不出來的。

有瀏覽器 MCP 工具就用它。**沒有的話用本機的 headless Chrome**, 不要直接把沒驗證過的東西丟給使用者:

```
"<chrome 路徑>" --headless=new --disable-gpu --hide-scrollbars --window-size=1180,1830 --virtual-time-budget=5000 --screenshot=<out.png> <url>
```

- 畫布比視窗大時加 `--force-device-scale-factor=0.5` 縮著截, 一次看完整張
- **canvas 的 serve_url 帶 token, 不可以寫進任何會留下來的檔案**。要傳給 Chrome 就寫進暫存檔, 讀完立刻刪
- **檢查 SVG 要用 `<img src="file:///...">` 引用, 不要把 SVG 內容 inline 進 HTML** — SVG 沒有 width/height 屬性時 inline 會塌陷成看不見, 你會以為是自己畫錯

## 7. design skill 不可用時

退化為文字描述: 3 個方向各用文字描述配色與字體, 使用者選; 再對每種版型給 1 個文字版面方案 (各元素位置以英吋描述), 直接寫 STYLE.md 並試 build 給使用者看 pptx。

## 完成條件

STYLE.md 存在且標定案, yaml 涵蓋 SLIDES.md 用到的全部版型, 使用者確認。STATUS.md 的 stage 改為「生簡報」。
