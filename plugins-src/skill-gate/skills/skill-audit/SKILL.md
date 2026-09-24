---
name: skill-audit
description: Use when a skill directory (SKILL.md and its supporting files) was created or modified, when a git commit is denied by the skill-audit gate, or when the user asks to audit, review, optimize, or health-check a skill's text (「優化 skill」「skill 優化」「檢查 skill」「skill 健檢」「skill health check」「檢查 {skill名稱}」). Static review of the skill's files, not running evals or benchmarking trigger accuracy. Applies to any skill, in any repo.
---

# skill-audit

對一個 skill 目錄逐項套用下方檢查清單, 先列出可優化項目讓使用者挑選, 只修使用者選中的項目。

## 輸入

- commit 關卡擋下時, 擋下訊息會列出要檢查的 skill 目錄, 逐一處理
- 使用者指定 skill 名稱或路徑時, 處理該目錄
- 都沒有時, 取當前 repo 裡有變更(staged 或未 staged)且含 SKILL.md 的目錄
- 仍找不到時, 若工作中的專案根目錄有 skill 索引檔(如 `SKILLS.md`), 列出其中的 skill 編號清單讓使用者選; 否則問使用者

## 流程

1. **前置檢查**: 目錄存在且含 SKILL.md(不分大小寫)。不符就告知使用者並中止
2. **讀取**: 讀目錄內所有文字檔(含子目錄的 .md 與腳本)。只讀這個 skill 目錄, 不讀它提到的外部大檔
3. **檢查**: 逐項對照「檢查清單」, 記下每個問題的所在檔案與段落、問題、建議改法。這一步不改檔
4. **列出並等待選擇**: 依下方「建議清單格式」輸出, 然後停下等使用者回覆。沒有任何問題時輸出無問題格式後直接跳到收尾
5. **套用**: 只修使用者選中的項目。動手前確認目錄在 git 版控下(`git -C <目錄> rev-parse`); 不在版控下就先把整個目錄複製到暫存區當備份, 並在回報中寫出備份位置
6. **驗證**: 重讀改過的檔案, 確認 frontmatter 仍是合法 YAML、`name` / `description` 都在、所有 step 引用與檔案引用都對得上。驗證不過就修到過為止
7. **收尾**: 若這次是被 commit 關卡擋下的, 把改過的檔案 `git add`, 再照擋下訊息給的指令登記已檢查(`node <本 SKILL.md 所在目錄>/gate.js --stamp <skill 目錄> --stamp-file <指紋檔>`, 指紋檔路徑以擋下訊息為準, 自己猜的路徑會跟關卡讀的對不上), 然後重跑原本的 commit。使用者一項都不選時同樣要登記, 否則 commit 會一直被擋
8. **回報**: 逐項列出已修正的內容(檔名 + 改了什麼), 提醒可用 `git diff` 檢視

## 建議清單格式

```
## Skill 優化建議: {skill 名稱}

1. `{檔名}` {段落} — {問題}
   → {建議改法}
2. ...

請回覆要修正的編號(例如「1, 3」)、「全部」, 或「都不修」。
```

判斷不確定是刻意設計還是問題的項目, 在該項末尾加「(可能是刻意設計)」, 讓使用者決定。

沒有任何問題時輸出:

```
## Skill 優化建議: {skill 名稱}

✅ 未發現需要優化的項目。
```

## 修正原則

- 修正只改寫法, 不改 skill 原本要達成的行為與適用範圍
- 拆出新檔(腳本、reference)時, 同步把原處改成引用, 路徑從本 SKILL.md 所在位置推算

## 檢查清單

**Frontmatter 與觸發**
- `name` 只用小寫字母、數字、連字號, 不超過 64 字元; `description` 不超過 1024 字元
- description 用第三人稱, 同時交代做什麼情境下用、帶使用者會說的關鍵詞
- description 只寫觸發條件, 不摘要流程——摘要流程會讓 agent 照 description 做而跳過本文
- description 寫得積極一點, 列出相近說法; Claude 傾向少觸發, 保守的描述會漏觸發
- 觸發詞不過度寬泛, 不與其他 skill 的觸發詞重疊(對照同一 skills 目錄下其他 SKILL.md 的 description)

**內容**
- 通用性: 內容若過度針對某次任務、某個專案或某個特例(特定版本、特定機器、特定事件), 抽出背後的通則, 讓 skill 涵蓋它原本應有的應用範圍; 特例若真的必要, 降為通則下的舉例
- 不寫死會隨內容增減而變動的數量(項目數、步驟數、檔案數等), 改用不帶數量的說法, 避免增刪時漏改
- 刪掉 Claude 本來就知道、不值其 token 成本的解釋
- 指令精確度與任務風險相符: 易出錯、要求一致的操作給精確指令或腳本; 需要依情境判斷的給原則
- 同一概念全文用同一個詞
- 不寫會過期的資訊(日期條件、「目前最新版」); 真要保留舊做法, 集中到一個「舊做法」段落
- 不列一串並列選項; 給一個預設做法, 另附例外情況
- 講原因, 少用全大寫 MUST / ALWAYS 施壓; 真正的硬規則保留, 但附上理由

**結構與 token**
- SKILL.md 本文超過約 500 行時, 把細節拆成 reference 檔; reference 只從 SKILL.md 直接連過去, 不再往下巢狀; 超過約 100 行的 reference 開頭加目錄
- 不在使用者縮小範圍前預讀大量檔案, 不一次掃整個目錄; 改成先讓使用者選, 或分批、懶載入
- 同一份資料不在多個步驟重複讀取, 讀一次後沿用
- 同一條規則、格式、清單只在一處定義, 其他地方引用該處(單一事實來源)
- 內嵌的長樣板(HTML、大段文字模板)或長段可執行程式碼, 抽成獨立檔案, SKILL.md 改為引用或呼叫
- 一個 skill 裡有多個可各自觸發、彼此沒有資料依賴的流程時, 拆成多個 skill

**健壯性**
- 寫死本機路徑: 不寫死絕對路徑(專案、工具、skill 自身), 改從本 SKILL.md 所在位置推算, 或讀環境變數並附 fallback(能推算出合理預設就用預設, 推不出來就讓 skill 在執行時詢問使用者); 傳給 sub-agent 的字串同樣適用。例: 專案根目錄讀 `$env:LOBBY_ROOT` 時寫成 `if ($env:LOBBY_ROOT) { $env:LOBBY_ROOT } else { Get-Location }`
- 依賴的前置條件(環境變數、檔案、工具、套件)在開頭檢查, 缺少時給明確錯誤訊息
- 破壞性操作(覆寫、刪除、reset)前有確認或備份, 並寫明怎麼還原
- 步驟之間有成功驗證, 上一步失敗就中止, 不繼續往下
- 不引用不存在的 step(重新編號後殘留的跳轉)
- 引用的檔案、腳本實際存在於 skill 目錄或寫明的位置; 不存在又無從得知其內容時, 建議改法寫「請提供該檔內容或移除引用」, 不自行補寫
- 腳本自己處理錯誤, 不丟給 agent 收拾; 常數附上取值理由; 寫清楚是要「執行」還是「讀來參考」
- MCP 工具寫完整名稱(`Server:tool`)
- 給 sub-agent 的指令帶足 context: 要讀哪份規範、輸出什麼格式、結果回傳什麼

**Memory 汙染**
- 為什麼要查: Claude 的 auto-memory 存在 `~/.claude/projects/<啟動目錄>/memory/`, 不進 git 且綁定啟動目錄, 只有「這台機器 + 這個啟動目錄」讀得到。skill 建置或測試期間學到的東西(踩坑、環境限制、必要步驟、失敗模式)若落在 memory, 當下 skill 看似跑得順, 實際是「skill + 本機 memory」的組合; 換機器、換人、換啟動目錄就不如預期, 而且測試當下看不出來
- 怎麼查: 掃 `~/.claude/projects/*/memory/` 底下所有目錄(不只目前的啟動目錄, 殘留常在別處), 找出提到這個 skill 名稱、觸發詞或其流程的內容
- 建議改法: skill 執行需要知道的寫進該 skill 的 SKILL.md(或其 reference 檔); 與這個 skill 無關的通則不在本次處理, 列出來讓使用者自行決定去處; 搬完刪除該 memory 檔與 MEMORY.md 裡對應的索引行
- 這一類的建議項目標明「本機 memory」: 改的是使用者本機檔案, 不會出現在 commit 裡
