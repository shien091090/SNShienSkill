# Commit 規範

任何 commit 前重讀本檔全文再下手。不憑記憶, 也不抄 `git log` 裡舊 commit 的寫法——舊 history 不保證合規, 本檔才是權威。

## 專案規範優先

專案內若有明確定義的 commit 規範(repo 根目錄的 CLAUDE.md、`.claude/rules/`、CONTRIBUTING 等), **一律以專案的為主**, 本檔退為 fallback。衝突時不自己折衷、不混用兩邊格式, 照專案那份走; 專案沒講到的部分才回來套本檔。

判斷不出哪份是現行規範就停下來問使用者, 不要憑 `git log` 舊 commit 猜。

例: `D:\Git\MYS-808` 的 `aiToolLib/.claude/rules/22-commit-and-safety-guardrails.md` 自稱最高優先, 要求「嚴禁自動 commit, 必須等使用者明確指示」且 message 走 Conventional Commits 前綴——這兩條分別蓋過本檔的「預設行為」與「格式」。

## 預設行為

改動完成後直接 `git commit`, 不用問。push 一律等使用者明確指示。

## 操作流程

1. 涉及 submodule 時, 先進 submodule 目錄 commit, 拿到短 SHA(或確認落在哪個 Tag)後才回主專案 commit
2. submodule 若是 detached HEAD, **停下來問**要不要 checkout 到 develop(或其他 branch), 不可自己決定——detached 上的 commit 推不出去, 會變孤兒。確認後: `git merge-base --is-ancestor <branch> HEAD` 確認是祖先 → `git checkout <branch>` → `git merge --ff-only <原 detached SHA>`
3. `git add` 後、commit 前, 跑一次**不帶 pathspec** 的 `git status --short`, 確認 staging 裡只有這次要 commit 的檔案(工作區常有使用者自己的工具產物已 staged)。commit 完才發現帶錯且尚未 push: `git reset --soft HEAD~1` 重新分開 commit

## 格式

```
[{前綴}] [{系統名稱}] [{次要功能名稱,非必要}] {內容}
```

只寫一行標題, 不寫 body。description 留空, 除非需要列清單說明特殊狀況。

前綴:
- `feat` 功能實作/調整, 含程式碼、Prefab、ScriptableObject、動畫
- `fix` 修正 Issue, description 附 Issue 單連結
- `data` 本地資料表: CardRelease、字表、Excel
- `docs` 規格書、SKILL.md、開發文件(純文字, 非資料表)
- `auto` 純 Unity 工具產物: PackingSpriteAtlas、TextureImport、meta
- `plug` 第三方插件/Dll 導入設定(改插件原始碼本身用 `feat`)
- `test` 單元測試、純測試用程式碼
- `other` 其他

## 內容

- 單一項目直接接在最後一個 `]` 後空一格; 多項目 `1.XXXX 2.XXXX`(數字 + 半形空格)
- **一個數字項目只講一件事**。句子裡出現「；」「，並」「，順便」「，另外」幾乎都是在講第二件事, 拆成獨立項目, 不能靠標點帶過
- 概述做了什麼, 不寫實作細節, 不寫測試狀態(「測試28個全過」不寫)
- **不出現英文程式碼識別字**(function / class / const 名), 轉成中文描述行為:
  - ✗ `修正RequestMemberQualificationAsync發送RequestApi事件參數型別錯誤(帶DRT_ApiType非DRT_ApiRequestParams)導致cast失敗`
  - ✓ `修正資格賽結束後重新請求資格API時, 事件參數型別帶錯導致轉型失敗`
  - 例外: 團隊已慣用的固定稱呼(如 `CentToCredit`)直接寫英文, 不硬翻。判準是「這個詞是不是專案裡大家已經在用的稱呼」; 這次改動才取的內部命名(如 `hasOngoingMatch`)才要避免

## Submodule

- 簡寫只有 `ThirdParty` → `3P`; `aiToolLib` 與其他一律全名, 不自己發明縮寫
- 版本: 落在 Tag 上用 Tag 名(`4.3.381`), 否則 7~8 碼短 SHA
- 純 bump 無功能開發: 不加任何標籤, 直接 `update aiToolLib to 51224bb`
- 搭配功能開發: 照常規格式, submodule 更新拆成內容裡的一個數字項目, 固定寫 `update {簡寫或全名} to {版本}`
  例: `[feat] [分組日榜] [玩家明日賽事資格管理器] 1.實作玩家明日賽事資格管理器模塊與測試 2.update 3P to 32f54e4`

## 專案別例外: 不加 `[前綴]`

- `D:\Git\lobby-agent-client`: `[{Skill中文名}] [{次要功能,非必要}] {內容}`, 系統名放該次改動所屬 skill 的中文名(如 `[拆解模塊]`), 不加 `[Skill]` 分類標籤
- `D:\Git\808_Lobby_6000\aiToolLib`: `[{規範中文名}] {內容}`(如 `[Unit Test規範]`), 這個 repo 歷史本來就無前綴
