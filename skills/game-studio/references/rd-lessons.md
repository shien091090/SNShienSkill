# RD 經驗

只有 RD agent 讀寫。每條三行內: `- (症狀) → (原因) → (解法)`。跨遊戲通用, 不寫單一遊戲的參數。同類問題合併, 不重複。

## Canvas / 渲染
- 高 DPI 螢幕畫面模糊 → canvas 實際像素等於邏輯尺寸 → `canvas.width = logical * devicePixelRatio`, 再 `ctx.scale(dpr, dpr)`, CSS 尺寸維持邏輯值
- 文字或線條位置偶爾糊一像素 → 座標落在半像素 → 靜態元素座標 `Math.round`, 或 1px 線條偏移 0.5

## 載入 / 檔案
- 雙擊 index.html 開啟後 console 報 CORS, 腳本沒跑 → `type="module"` 在 `file://` 下被瀏覽器擋 → 一律用傳統 `<script src>`, 用全域物件溝通

## 輸入
- 按方向鍵或空白鍵頁面會捲動 → 瀏覽器預設行為 → keydown 裡對遊戲用到的鍵 `e.preventDefault()`
- 按住鍵一直觸發跳躍 → keydown 會重複觸發 → 用 `e.repeat` 過濾, 或維護 pressed 集合只在狀態轉變時動作

## 計時 / 遊戲循環
- 切到別的分頁再回來, 物件瞬移或穿牆 → requestAnimationFrame 暫停後 dt 累積過大 → `dt = Math.min(dt, 1/30)` 之類上限
- 不同螢幕更新率速度不同 → 用幀數而非時間推進 → 所有移動乘 dt

## 其他
