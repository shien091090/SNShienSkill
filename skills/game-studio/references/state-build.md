# 狀態: build Demo 版實作

續接: game/art/ 兩檔已齊 → 不再 spawn 美術; game/audio/ 的 sound.js 與 sound.md 已齊 → 不再 spawn 音效; 兩者都齊才 spawn RD; game/index.html 已存在 → 直接做「你處理回報」的核對, 不重做。只齊一邊時, 只補 spawn 缺的那一邊。

兩條路徑, 看是從哪裡進來的。STATE.md 的 log 由下往上找最近一條含「進 build」的事件: 含「spec v… 通過, 進 build 完整實作」→ 完整實作; 含「進 build 美術修正」「進 build 音效修正」或「進 build 美術與音效修正」→ 修正路徑(只跑 log 寫到的那幾種)。

## 完整實作

### 開工前: 上一版產物歸檔

`game/` 內已有上一個可玩版本 → 整包搬到 `archive/game-v<該版的 spec 版號>/`, 再建空的 `game/art/` 與 `game/audio/`。這個目錄就是下面說的「上一版美術交付」與「上一版音效交付」(上一版沒有 audio/ 就是沒有音效交付)。

### 美術與音效並行

美術與音效**同時 spawn**(同一則訊息兩個 Agent 呼叫), 互不等待、互不讀對方的檔。兩邊都交付並通過你的檢查後, 才 spawn RD。spec 沒有「音效清單」章節或清單寫「無」時不 spawn 音效。

### 視覺設計預設沿用上一版

有上一版美術交付時, **預設沿用**它的視覺語言(色票、形狀語言、各物件的畫法、畫面版面骨架), 美術只重做規格變動牽涉到的物件: 規格刪除的物件連同函式刪掉, 新增的物件照同一套視覺語言設計, 沒變的物件照原樣保留。理由: 老闆每版都要重新熟悉畫面, 且他給過的具體美術回饋會在整套重畫時流失。代價是上一版的缺點也會被沿用, 靠美術回饋修。

例外, 改為整套重新設計(清單不帶上一版美術交付, 任務刪掉「沿用」那句):
- 規格變動讓上一版的版面骨架不再適用(例: 畫面上的主要區塊被整個刪掉或新增)
- 老闆明說要重新設計

由你判斷, 理由寫進進 build 那一行 log。

### 美術

spawn `game-artist`:
```
狀態: build, 美術
請讀取: <game>/spec.md、<game>/guide.md、~/.claude/skills/game-studio/references/art-lessons.md、<game>/archive/game-v<上一版>/art/style.md 與 art.js(有上一版美術交付且沿用時才列)
任務: 依規格「物件清單」產出 <game>/game/art/art.js 與 <game>/game/art/style.md。有上一版美術交付時, 沿用它的視覺語言與版面骨架, 只重做規格變動牽涉到的物件(刪除的物件連同函式刪、新增的照同一套視覺語言設計、沒變的保留原畫法與函式名)。畫布邏輯尺寸依「數值參數表」的畫面寬高。另依 guide.md 每頁的「圖要示意什麼」畫出玩家說明的示意圖(函式 drawGuidePage(ctx, state), state 至少含頁碼; 圖裡的遊戲物件直接用遊戲內的畫法)。開工前先讀經驗文件(設計理念與經驗兩層), style.md 要有「理念落實」一節; 收工前依它的規則回寫。
輸出格式: 回報產了哪些 draw 函式(沿用時分列: 保留 / 修改 / 新增 / 刪除)、畫布尺寸、判斷不需獨立函式的物件與理由、以及回寫了哪幾條經驗與理念異動(新增候選 / 升格 / 縮邊界 / 降格, 各附證據; 沒有就說無)
```

若 `feedback/` 內有尚未處理的美術回饋(上一輪 playtest 同時有玩法與美術回饋、走了退回路徑), 檔案清單加 `<game>/feedback/round-<round.playtest>.md`, 任務加一句「同時參考 feedback 的美術段」。這是完整實作路徑除上一版美術交付之外唯一允許多帶的檔。

你檢查: `game/art/` 只有這兩檔; style.md 有物件表且每個函式簽章與 state 欄位寫全, 且有「理念落實」一節; guide.md 每一頁都有對應的示意圖。不齊 → SendMessage 同 agent 補。

### 音效

spawn `game-audio`(與美術同一則訊息):
```
狀態: build, 音效
請讀取: <game>/spec.md、~/.claude/skills/game-studio/references/audio-lessons.md、<game>/archive/game-v<上一版>/audio/sound.md 與 sound.js 與 credits.md(有上一版音效交付時才列)
任務: 依規格「音效清單」產出 <game>/game/audio/ 下的 sound.js、sound.md、credits.md 與 assets/。素材先從線上找免費授權資源, 搜過仍找不到合適的事件才用 Web Audio 程式產生。有上一版音效交付時, 沿用它的素材與聲音風格, 只為規格新增或改變的事件找新素材。開工前先讀經驗文件, 收工前依它的規則回寫。
輸出格式: 回報每個事件用了哪個素材(或程式產生與理由)、授權統計、總檔案大小、以及回寫了哪幾條經驗(沒有就說無)
```

若 `feedback/` 內有尚未處理的音效回饋, 檔案清單加 `<game>/feedback/round-<round.playtest>.md`, 任務加一句「同時參考 feedback 的音效段」。

你檢查: sound.md 事件表涵蓋 spec 音效清單每一條, 事件名、呼叫時機、opts 寫全; credits.md 每個音檔都有來源網址與授權, 授權只能是 CC0 / 公有領域 / CC-BY(已署名)/ 免署名可商用; 沒有 CDN 或 fetch 讀音檔。不齊 → SendMessage 同 agent 補。

### RD(美術與音效都交付後才 spawn)

spawn `game-rd`:
```
狀態: build, RD
請讀取: <game>/spec.md、<game>/telemetry.md(存在才列)、<game>/guide.md、<game>/game/art/style.md、<game>/game/audio/sound.md(有音效交付才列)、~/.claude/skills/game-studio/references/rd-lessons.md
任務: 依規格實作 <game>/game/index.html(可拆 game.js / style.css), 繪製一律呼叫 game/art/art.js 提供的 Art.drawXxx; 聲音一律呼叫 game/audio/sound.js 提供的 Sound.play / playMusic, 在第一次按鍵時呼叫 Sound.init(), 載入順序 art/art.js → audio/sound.js → game.js。另依 guide.md 做玩家說明畫面: 開場先顯示、可翻頁、遊戲中可再叫出, 文字照 guide.md, 圖呼叫 Art.drawGuidePage。所有操作(含說明翻頁與關閉)只用規格「操作」章節列的那一種輸入, 不掛另一種輸入的事件監聽。依 telemetry.md(沒有就依規格「埋點」章節)逐筆與逐局記錄, 每局結束自動下載一個 JSON 檔, 檔名 gamelog-<遊戲資料夾名>-<YYYYMMDD-HHMMSS>.json。開工前先讀經驗文件, 收工前依它的規則回寫。
輸出格式: 四段回報(做了什麼 / 佔位圖形 / 規格疑問 / 經驗文件)
```

你處理回報:
- 佔位圖形非空 → SendMessage 給**美術**(同狀態內可續)補函式; 補完 SendMessage RD 接上。完整實作路徑中, 這是唯一允許美術新增函式的情況; 美術修正路徑的新增函式規則見下節。RD 接上後刪掉對應的 Placeholder 條目
- 規格疑問非空 → 你判斷: 規格層小洞你直接裁決告訴 RD; 真的是規格矛盾 → 這裡不修規格, 記進 log(寫在該次進 build 那一行的後面, 不另起新行), 等 playtest 一起走退回
- 你沒有瀏覽器, 不得聲稱自己玩過。改用讀碼核對: 開 `index.html` 確認 script 載入順序是 `art/art.js` →(有音效時)`audio/sound.js` → `game.js` 且沒有 `type="module"`; 有音效時確認 sound.md 每個事件在 game.js 都有呼叫點、靜音鍵照 spec 接上; 確認 RD 回報有跑 `node --check`; 逐條對 spec 的規則、操作、結束條件在 `game.js` 找到對應程式; 執行守則中標記 build 的條目(R1: 沒有另一種輸入的監聽; R2: 說明畫面存在且文字與 guide.md 一致; R3: 紀錄欄位與 telemetry.md 一致、每局結束會觸發下載、檔名合規)。對不上 → 當 bug 走 SendMessage RD 修, 不轉移。實際可玩性由使用者在 playtest 第一件事確認

## 修正路徑(從 playtest 進來)

log 寫了哪幾種就跑哪幾種; 美術修正與音效修正都要跑時**同一則訊息並行 spawn**, 兩邊都收工後再決定要不要 spawn RD。

### 美術修正

spawn `game-artist`(新 session):
```
狀態: build, 美術修正
請讀取: <game>/spec.md、<game>/game/art/style.md、<game>/feedback/round-<round.playtest>.md、~/.claude/skills/game-studio/references/art-lessons.md
任務: 只看 feedback 的「美術」段, 修改 game/art/art.js 與 style.md 回應這些回饋。不改既有函式名與參數。開工前先讀經驗文件, 每條回饋動手前先判定它違反了哪條理念; 收工前依它的規則回寫。
輸出格式: 逐條回饋說明違反了哪條理念(或無)、改了什麼; 若有新增函式列出來; 回寫了哪幾條經驗與理念異動(新增候選 / 升格 / 縮邊界 / 降格, 各附證據; 沒有就說無)
```

- 沒新增函式 → 你讀 art.js 的 diff 確認每條美術回饋都有對應改動
- 有新增函式 → 記下, 與音效新增的事件一起交 RD(見下)

### 音效修正

spawn `game-audio`(新 session):
```
狀態: build, 音效修正
請讀取: <game>/spec.md、<game>/game/audio/sound.md、<game>/game/audio/credits.md、<game>/feedback/round-<round.playtest>.md、~/.claude/skills/game-studio/references/audio-lessons.md
任務: 只看 feedback 的「音效」段, 修改 game/audio/ 回應這些回饋。不改既有事件名與 opts 欄位。換素材時照樣先找線上免費授權資源, 並更新 credits.md。開工前先讀經驗文件, 收工前依它的規則回寫。
輸出格式: 逐條回饋說明改了什麼(換了哪個素材、音量怎麼調); 若有新增事件列出來; 回寫了哪幾條經驗(沒有就說無)
```

- 沒新增事件 → 你讀 sound.md 與 credits.md 的 diff 確認每條音效回饋都有對應改動, 授權合規

### 修正後接 RD

- 美術沒新增函式、音效也沒新增事件 → 直接轉移
- 有任一新增 → spawn `game-rd`, prompt 同完整實作的 RD 版, 任務改為「style.md 新增了 <函式> / sound.md 新增了事件 <名稱>, 請在對應位置接上, 其他不動」

## 轉移

照 SKILL.md 轉移程序 → `playtest`(round.playtest +1), 照模板建 feedback/round-<round.playtest>.md(用 +1 後的新輪號)。回報使用者: 遊戲路徑(可直接雙擊的絕對路徑)、請他試玩並回饋。操作說明不在回報裡重寫, 遊戲開場的說明畫面就是給他看的。
