# 狀態: build Demo 版實作

兩條路徑, 看是從哪裡進來的(STATE.md log 最後一行):
- 從 spec-review 通過進來 → **完整實作**: 美術 → RD
- 從 playtest 美術回饋進來 → **美術修正**: 美術 → (視需要)RD

## 完整實作

### 美術

spawn `game-artist`:
```
狀態: build, 美術
請讀取: <game>/spec.md
任務: 依規格「物件清單」產出 <game>/game/art/art.js 與 <game>/game/art/style.md。畫布邏輯尺寸依「數值參數表」的畫面寬高。
輸出格式: 回報產了哪些 draw 函式、畫布尺寸、判斷不需獨立函式的物件與理由
```

若 `feedback/` 內有尚未處理的美術回饋(上一輪 playtest 同時有玩法與美術回饋、走了退回路徑), 檔案清單加 `<game>/feedback/round-<N>.md`, 任務加一句「同時參考 feedback 的美術段」。這是完整實作路徑唯一允許多帶的檔。

你檢查: `game/art/` 只有這兩檔; style.md 有物件表且每個函式簽章與 state 欄位寫全。不齊 → SendMessage 同 agent 補。

### RD(美術產出後才 spawn)

spawn `game-rd`:
```
狀態: build, RD
請讀取: <game>/spec.md、<game>/game/art/style.md、~/.claude/skills/game-studio/references/rd-lessons.md
任務: 依規格實作 <game>/game/index.html(可拆 game.js / style.css), 繪製一律呼叫 game/art/art.js 提供的 Art.drawXxx。開工前先讀經驗文件, 收工前依它的規則回寫。
輸出格式: 四段回報(做了什麼 / 佔位圖形 / 規格疑問 / 經驗文件)
```

你處理回報:
- 佔位圖形非空 → SendMessage 給**美術**(同狀態內可續)補函式; 補完 SendMessage RD 接上。這是唯一允許美術新增函式的情況
- 規格疑問非空 → 你判斷: 規格層小洞你直接裁決告訴 RD; 真的是規格矛盾 → 這裡不修規格, 記進 log, 等 playtest 一起走退回
- 自己開 `game/index.html` 玩三十秒: 能開、能操作、能結束。開不了或明顯不照規格 → 當 bug 走 SendMessage RD 修, 不轉移

## 美術修正(從 playtest 進來)

spawn `game-artist`(新 session):
```
狀態: build, 美術修正
請讀取: <game>/spec.md、<game>/game/art/style.md、<game>/feedback/round-<N>.md
任務: 只看 feedback 的「美術」段, 修改 game/art/art.js 與 style.md 回應這些回饋。不改既有函式名與參數。
輸出格式: 逐條回饋說明改了什麼; 若有新增函式列出來
```

- 沒新增函式 → 你開遊戲確認畫面有變, 直接轉移
- 有新增函式 → spawn `game-rd`, prompt 同完整實作的 RD 版, 任務改為「style.md 新增了 <函式>, 請在對應位置接上, 其他不動」

## 轉移

照 SKILL.md 轉移程序 → `playtest`(round.playtest +1), 照模板建 `feedback/round-<N>.md` 空檔。回報使用者: 遊戲路徑(可直接雙擊的絕對路徑)、操作方式一句、請他試玩並回饋。
