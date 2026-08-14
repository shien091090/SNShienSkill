---
name: feedback-auto-commit-format
description: 改動完成後預設自動 git commit（不 push），commit message 需依固定前綴＋格式撰寫，內容盡量避免全英文程式碼細節改用中文敘述
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 37ad5b1b-af29-4350-b379-569fd5b4f94f
  modified: 2026-08-11T02:36:05.791Z
---

不論在哪個專案，程式碼／檔案改動完成後，預設直接自動執行 `git commit`（不 push），不需再詢問是否要 commit。commit message 依下列固定格式撰寫。

**Why:** 使用者希望改動完成就留下版控紀錄，push 時機仍要自己控制，所以「commit」和「push」的自動化程度不同：commit 直接做，push 要等明確指示。

**How to apply:**

commit message 格式：
```
[{前綴}] [{系統名稱}] [{次要功能名稱,非必要}] {內容}
```

前綴規範：
- `feat`：功能實作、調整、修改等變動（含程式碼、Prefab、ScriptableObject、動畫等）
- `fix`：修正 Issue（description 附上 Issue 單連結）
- `data`：更新本地資料表，含 CardRelease、字表、其他 Excel 文件
- `docs`：規格書、SKILL.md、開發文件等文件類異動（純文字說明/規格內容調整，非資料表）
- `auto`：純粹執行 Unity 工具產生的變動，如 PackingSpriteAtlas、TextureImport 或自動產生的 meta 檔
- `plug`：第三方插件或外部 Dll 導入/設定（更動第三方插件開源程式碼本身時改用 `feat`）
- `test`：單元測試或純測試用程式碼（下 Log、測試流程等）
- `other`：其他

內容規範：
- 單一項目：內容直接接在最後一個 `]` 標籤後面，中間空一格
- 多項目：以數字符號＋半形空格分隔，例如 `1.XXXX 2.XXXX 3.XXXX`
- **一個數字項目只講一件事**：如果一句話裡實際包含兩件不同的事（例如「實作A模塊，並整併B模塊的職責」），要拆成兩個獨立的數字項目，不要合併成一句話帶過兩個動作
- **實作內容龐大時，不需要把實作細節寫進 commit message**，尤其是變數/欄位名稱（如 `hasOngoingMatch`、`lastReportedState` 這類內部命名）——只需要簡單概述做了什麼，細節看程式碼本身即可
- **⚠️ 2026-08-04 起：盡可能不要在內容裡出現全英文的程式碼細節**，包含 function name／class name／const 字串等（例如 `RequestMemberQualificationAsync`、`DRT_ApiType`、`DRT_ApiRequestParams` 這類具體實作識別字），要轉成中文好懂的敘述描述「做了什麼」，不要直接貼程式碼識別字。例如不要寫「修正RequestMemberQualificationAsync發送RequestApi事件參數型別錯誤(帶DRT_ApiType非DRT_ApiRequestParams)導致cast失敗」，改寫成「修正資格賽結束後重新請求資格API時，事件參數型別帶錯導致轉型失敗」。系統名稱/模塊中文名稱（如「資格倒數計時管理器」）本來就是中文，不受此規則限制
  - **⚠️ 但「專有名詞」不用勉強translate成中文**：像 `CentToCredit`（押分轉點數的共用擴充方法，專案裡是固定的專有名詞/慣用說法）這類已經是團隊慣用、直接講英文就懂的名詞，直接寫英文即可，不用硬翻成「押分轉點數」這種繞口的中文敘述——判斷標準是「這個詞本身是不是專案裡大家已經在用的固定稱呼」，如果是，保留英文；如果是這次改動才臨時取的內部變數/方法名（如 `hasOngoingMatch`），才需要避免出現、改用中文描述行為
- **不需要寫測試狀態**，例如「測試28個全數通過」這種敘述不用寫進 commit message
- description 欄位盡量留空，除非該次改動需要列清單說明特殊狀況才附上
- **只寫一行標題，不要另外加一段說明「為什麼」的內文（commit body）**。原因、脈絡這些留在對話紀錄或 PR 描述即可，commit message 本身要簡短，一行講完改了什麼就好，不需要展開解釋動機或背景

**例外（維持不自動 commit/push，見既有規則）：**
- GAS 專案 `gas_live_integration`：[[feedback_no_auto_gas_commit]]
- linebot 專案 `linebot_liveManagerIntegration`（除「更新GAS網址」skill 外）：[[feedback_no_auto_push_except_gas_url]]

**專案別格式例外：**
- `lobbyagents` 專案（現已改名為 `lobby-agent-client`，路徑 `D:\Git\lobby-agent-client`）：**完全不加 `[前綴]` 這個標籤**（不要 `[feat]`／`[docs]` 等，跟 `aiToolLib` 的例外規則一樣），也不需要加 `[Skill]` 這種分類標籤；`{系統名稱}` 欄位直接放該次改動所屬 Skill 的**中文名稱**（不是 skill 資料夾的英文代號），例如改動 `activity-decompose-module` 就寫 `[拆解模塊]`，比英文代號更直覺易懂。格式為 `[{Skill中文名稱}] [{次要功能名稱,非必要}] {內容}`。
- `aiToolLib` 專案（`D:\Git\808_Lobby_6000\aiToolLib`）：**完全不加 `[前綴]` 這個標籤**（不要 `[feat]`／`[fix]` 等），這個 repo 既有的 commit 歷史本來就沒有前綴（例如「新增共用模塊規範」），2026-07-17 之前有幾筆 commit 誤加了 `[feat]`/`[docs]` 前綴，不符合這個 repo 的既有慣例。`{系統名稱}` 之後的標籤（例如 `[Unit Test規範]`、`[MVP Model架構規範]`）維持照打，只是最前面不要再加 `[前綴]`

**改動涉及 submodule 時（例如 Slot_Lobby 的 `Assets/ThirdParty`、`aiToolLib`）：**
- Submodule 簡寫代稱：`ThirdParty` → `3P`；`aiToolLib` **不用簡寫**，直接寫全名。其他未特別指定簡寫的 submodule，預設也用全名，不要自己發明縮寫
- **純粹 bump submodule 版本（無其他功能開發內容）**：**完全不加** `[前綴] [系統名稱]` 這些標籤，直接寫 `update {簡寫或全名} to {版本}` 就好，例如 `update aiToolLib to 51224bb`
- **有搭配功能開發（該次改動隸屬於某個系統/功能）**：才照常規格式打 `[前綴] [系統名稱] [次要功能名稱]`，並把 submodule 更新拆成內容裡的其中一個項目（用既有的「多項目：數字符號＋半形空格」格式），寫法固定為 `update {簡寫或全名} to {版本}`
  - 該 submodule 目前這個 commit 點**剛好落在某個版號 Tag** 上 → `{版本}` 用該 Tag 名稱，例如 `update 3P to 4.3.381`
  - 沒有落在 Tag 上 → `{版本}` 用該 commit 的短 SHA（7~8碼），例如 `update 3P to 96e48db`、`update aiToolLib to 6798f04`
- **操作順序**：因為要拿到 submodule 那邊的 commit SHA 才能填進主專案的 commit message，所以必須**先進 submodule 目錄 commit**，拿到 SHA（或確認是否正好在某個 Tag 上）之後，**才回到主專案 commit**
- 範例（有功能開發）：`[feat] [分組日榜] [玩家明日賽事資格管理器] 1.實作DRT_PlayerQualificationManager模塊與測試 2.update 3P to 32f54e4`
- 範例（純 bump，無功能開發）：`update aiToolLib to 51224bb`
- **⚠️ Detached HEAD 處理**：在 submodule 目錄裡 commit 前，若發現該 submodule 目前是 **detached HEAD**（不在任何 branch 上），**不要自己擅自 checkout 到 develop 或任何 branch**——先停下來跟使用者確認是否要 checkout 到 `develop`（或其他指定 branch）再繼續 commit。這是因為 detached HEAD 上的 commit 無法 push，日後可能變成孤兒 commit 遺失，但要 checkout 去哪個 branch、由誰處理，必須每次都先問。
  - 確認要 checkout 後的安全做法：先確認目標 branch 是否為目前 detached commit 的祖先（`git merge-base --is-ancestor <branch> HEAD`），是的話用 `git checkout {branch}` + `git merge --ff-only {原本的detached commit SHA}` 做 fast-forward，避免產生非必要的 merge commit 或遺失變更

push 一律仍需使用者明確指示才執行，本規則只改變「commit」這一步的預設行為。

**⚠️ 2026-07-24 教訓：commit 前一定要看完整的 `git status`，不能只看要 commit 的那幾個檔案**：曾發生只對「這次要 commit 的 2 個檔案」做 `git status --short -- <files>` 確認乾淨，就直接 `git add <files> && git commit`，結果因為工作區裡剛好還有別的（例如使用者自己的「[auto] 刷新ViewsManager」工具跑出來、已經 staged 在 index 裡但還沒 commit）異動，被一起帶進了這次的 commit，造成 commit 內容跟訊息對不上。**正確做法**：`git add` 完要 commit 前，先跑一次完整、不加任何 pathspec 限制的 `git status --short`，確認 staging area 裡真的只有這次打算 commit 的檔案，才執行 `git commit`。若發現已經委出去（commit 完才發現），只要還沒 push，可以用 `git reset --soft HEAD~1` 取消最後一次 commit（保留為 staged 狀態）再重新分開 commit。

**⚠️ 2026-08-10 教訓：不要憑印象或抄 `git log` 裡舊 commit 的寫法來套用格式，尤其是 submodule 參照格式**：曾在寫涉及 `Assets/ThirdParty` 的 commit message 時，直接模仿 `git log` 觀察到的舊 commit 寫法 `（submodule ThirdParty@SHA）`，而不是回頭讀這份檔案核對規則——結果那個舊寫法本身就不符合規範（正確格式是把 submodule 更新拆成內容裡的一個數字項目 `update 3P to {短SHA(7~8碼)}`，不是 `(submodule Name@SHA)` 這種寫法），導致連續寫錯兩次 commit message 才被使用者糾正。**之後任何一次要下 commit（尤其只要牽涉到 submodule pointer 更新）之前，一定要重新讀這份檔案的完整內容再動手寫 message，不能只憑記憶或觀察 `git log` 裡的舊範例反推格式**——舊 commit history 不保證符合當前規範，只有這份檔案本身是權威來源。

**⚠️ 2026-08-11 教訓：內容裡出現兩件不同的事時，一律用數字項目分隔（`1.XXXX 2.XXXX`），不要用中文標點（頓號、分號「；」）或「並」「順便」這類連接詞把兩件事接在一起寫成一句話**：曾寫過「活動頁面關閉時改為執行所有頁面的關閉流程，取代原本只關閉最後一個頁籤的作法；順便補上測試輔助方法漏清...的缺漏」，用「；」接了兩件事，被使用者糾正後改成 `1.XXXX 2.XXXX` 才符合規範。之後下筆前主動檢查：內容裡如果出現「；」「，並」「，順便」「，另外」這類接續語氣，幾乎都代表在描述第二件事，要拆成獨立的數字項目，不能靠標點符號帶過。
