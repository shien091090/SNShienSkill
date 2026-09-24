# 狀態: build Demo 版實作

續接: game/art/ 兩檔已齊 → 跳過美術直接 spawn RD; game/index.html 已存在 → 直接做「你處理回報」的核對, 不重做。

兩條路徑, 看是從哪裡進來的。STATE.md 的 log 由下往上找最近一條含「進 build」的事件: 含「spec v… 通過, 進 build 完整實作」→ 完整實作; 含「進 build 美術修正」→ 美術修正。

## 完整實作

### 美術

spawn `game-artist`:
```
狀態: build, 美術
請讀取: <game>/spec.md、<game>/guide.md、~/.claude/skills/game-studio/references/art-lessons.md
任務: 依規格「物件清單」產出 <game>/game/art/art.js 與 <game>/game/art/style.md。畫布邏輯尺寸依「數值參數表」的畫面寬高。另依 guide.md 每頁的「圖要示意什麼」畫出玩家說明的示意圖(函式 drawGuidePage(ctx, state), state 至少含頁碼; 圖裡的遊戲物件直接用遊戲內的畫法)。開工前先讀經驗文件(設計理念與經驗兩層), style.md 要有「理念落實」一節; 收工前依它的規則回寫。
輸出格式: 回報產了哪些 draw 函式、畫布尺寸、判斷不需獨立函式的物件與理由、以及回寫了哪幾條經驗與理念異動(新增候選 / 升格 / 縮邊界 / 降格, 各附證據; 沒有就說無)
```

若 `feedback/` 內有尚未處理的美術回饋(上一輪 playtest 同時有玩法與美術回饋、走了退回路徑), 檔案清單加 `<game>/feedback/round-<round.playtest>.md`, 任務加一句「同時參考 feedback 的美術段」。這是完整實作路徑唯一允許多帶的檔。

你檢查: `game/art/` 只有這兩檔; style.md 有物件表且每個函式簽章與 state 欄位寫全, 且有「理念落實」一節; guide.md 每一頁都有對應的示意圖。不齊 → SendMessage 同 agent 補。

### RD(美術產出後才 spawn)

spawn `game-rd`:
```
狀態: build, RD
請讀取: <game>/spec.md、<game>/guide.md、<game>/game/art/style.md、~/.claude/skills/game-studio/references/rd-lessons.md
任務: 依規格實作 <game>/game/index.html(可拆 game.js / style.css), 繪製一律呼叫 game/art/art.js 提供的 Art.drawXxx。另依 guide.md 做玩家說明畫面: 開場先顯示、可翻頁、遊戲中可再叫出, 文字照 guide.md, 圖呼叫 Art.drawGuidePage。所有操作(含說明翻頁與關閉)只用規格「操作」章節列的那一種輸入, 不掛另一種輸入的事件監聽。依規格「埋點」章節逐筆與逐局記錄, 每局結束自動下載一個 JSON 檔, 檔名 gamelog-<遊戲資料夾名>-<YYYYMMDD-HHMMSS>.json。開工前先讀經驗文件, 收工前依它的規則回寫。
輸出格式: 四段回報(做了什麼 / 佔位圖形 / 規格疑問 / 經驗文件)
```

你處理回報:
- 佔位圖形非空 → SendMessage 給**美術**(同狀態內可續)補函式; 補完 SendMessage RD 接上。完整實作路徑中, 這是唯一允許美術新增函式的情況; 美術修正路徑的新增函式規則見下節。RD 接上後刪掉對應的 Placeholder 條目
- 規格疑問非空 → 你判斷: 規格層小洞你直接裁決告訴 RD; 真的是規格矛盾 → 這裡不修規格, 記進 log(寫在該次進 build 那一行的後面, 不另起新行), 等 playtest 一起走退回
- 你沒有瀏覽器, 不得聲稱自己玩過。改用讀碼核對: 開 `index.html` 確認 script 載入順序是 `art/art.js` → `game.js` 且沒有 `type="module"`; 確認 RD 回報有跑 `node --check`; 逐條對 spec 的規則、操作、結束條件在 `game.js` 找到對應程式; 執行守則中標記 build 的條目(R1: 沒有另一種輸入的監聽; R2: 說明畫面存在且文字與 guide.md 一致; R3: 紀錄欄位與規格「埋點」章節一致、每局結束會觸發下載、檔名合規)。對不上 → 當 bug 走 SendMessage RD 修, 不轉移。實際可玩性由使用者在 playtest 第一件事確認

## 美術修正(從 playtest 進來)

spawn `game-artist`(新 session):
```
狀態: build, 美術修正
請讀取: <game>/spec.md、<game>/game/art/style.md、<game>/feedback/round-<round.playtest>.md、~/.claude/skills/game-studio/references/art-lessons.md
任務: 只看 feedback 的「美術」段, 修改 game/art/art.js 與 style.md 回應這些回饋。不改既有函式名與參數。開工前先讀經驗文件, 每條回饋動手前先判定它違反了哪條理念; 收工前依它的規則回寫。
輸出格式: 逐條回饋說明違反了哪條理念(或無)、改了什麼; 若有新增函式列出來; 回寫了哪幾條經驗與理念異動(新增候選 / 升格 / 縮邊界 / 降格, 各附證據; 沒有就說無)
```

- 沒新增函式 → 你讀 art.js 的 diff 確認每條美術回饋都有對應改動, 直接轉移
- 有新增函式 → spawn `game-rd`, prompt 同完整實作的 RD 版, 任務改為「style.md 新增了 <函式>, 請在對應位置接上, 其他不動」

## 轉移

照 SKILL.md 轉移程序 → `playtest`(round.playtest +1), 照模板建 feedback/round-<round.playtest>.md(用 +1 後的新輪號)。回報使用者: 遊戲路徑(可直接雙擊的絕對路徑)、請他試玩並回饋。操作說明不在回報裡重寫, 遊戲開場的說明畫面就是給他看的。
