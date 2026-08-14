---
name: reference-decompose-iterate-module-merge
description: lobbyagents的activity-decompose-module與activity-iterate-module在2026-07-17合併重構，單一模塊處理邏輯唯一權威來源是iterate-module
metadata:
  node_type: memory
  type: reference
  originSessionId: 176f2d81-e077-4c2f-9332-ac215d7b56de
---

`lobbyagents`（`D:\Git\lobbyagents`）的 `Skills/Lobby/ActivityDev/activity-decompose-module/SKILL.md` 與 `activity-iterate-module/SKILL.md` 在 2026-07-17 做了合併重構，原因是兩邊各自維護「怎麼實作一個模塊」的流程，改一邊常常忘記同步另一邊，導致 step 編號互相引用對不上（曾經發生過）。

**重構後的分工：**
- **拆解模塊**：只保留「從零蓋整個模塊地圖」的批次工作——蒐集敘述、比對前端規格找缺口、查共用模塊、批次建立所有模塊空殼、寫架構文件初稿，然後**迴圈呼叫「迭代模塊」**逐一處理每個待處理模塊，最後統一驗證與回報
- **迭代模塊**：擁有「怎麼處理單一模塊」的唯一權威邏輯（分支判斷、換手、實作、ViewPresenter檢查、串接進Model、更新架構文件），有兩種進入方式：
  - 獨立觸發（使用者直接喊「迭代模塊」）：完整跑分支偵測
  - 被拆解模塊迴圈呼叫：跳過偵測直接走「新增/首次實作」分支，且跳過它自己的驗證步驟（測試統一留給拆解模塊最後一次做）

**分支判斷邏輯的關鍵修正**：判斷一個模塊要走「新增/首次實作」還是「修改現有」，不是看檔案存不存在，而是看「class 本體是否仍是空殼」（對照架構文件「是否為待處理」欄位）——因為拆解模塊批次建立的空殼檔案本來就存在，但仍要走換手流程，不能因為檔案已存在就誤判成直接修改而跳過換手。

**How to apply：** 之後任何 session 要調整「單一模塊怎麼處理」的細節（換手怎麼問、ViewPresenter檢查、串接方式等），只需要改 `activity-iterate-module/SKILL.md`，不需要碰 `activity-decompose-module/SKILL.md`；除非要改的是兩者之間的呼叫介面本身（例如迭代模塊需要拆解模塊多傳什麼資訊），或是拆解模塊自己的批次蒐集/建空殼/迴圈終止邏輯，才需要動到拆解模塊。實際規則內容以當下讀取的 SKILL.md 為準，這份記憶只記錄「為什麼這樣分工」跟「改哪邊」，不要照抄裡面可能提到的舊步驟編號當作最新事實。
