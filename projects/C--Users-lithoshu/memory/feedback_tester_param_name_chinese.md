---
name: feedback-tester-param-name-chinese
description: LobbyIntegrationTester的[TesterFunction] customParameterName一律用中文,不要用英文欄位名(如previousLevel),方便QA在Debug面板上操作
metadata:
  node_type: memory
  type: feedback
  originSessionId: a495df67-c8b9-4ad1-98f3-c857a64a04ce
  modified: 2026-08-11T01:57:49.424Z
---

寫 `[TesterFunction(...)]` 帶自訂參數（`customParameterNameN`）時，參數名稱一律用中文，不要照抄程式碼裡的英文欄位名（例如 `previousLevel`/`currentLevel`）。

**Why：** 2026-08-11 在 `DailyRankTournamentTester` 新增3個通知彈窗測試功能時，一開始直接用英文欄位名當 `customParameterName`，被使用者糾正——這個名稱會直接顯示在 QA 操作的 Debug 面板參數輸入視窗上，用英文對不熟程式碼的 QA 不友善，改成中文（如「上一階級」「當前階級」）才好用。專案既有 Tester（`DailyRankTournamentViewTester`/`ChatTester`/`RewardEffectTester`）本來就都是中文參數名，這是既有慣例，不是這次才定的新規則。

**How to apply：** 之後任何新增/修改 `[TesterFunction]` 帶參數的方法，`customParameterNameN` 都要用中文描述該參數的意義；`parameterData.GetValue<T>(name)` 的 `name` 要跟 Attribute 內字串逐字一致（包含中文字），不要在方法內部又轉換成英文變數名時搞混兩者。這條規則已經隱含在 `rules/20-lobby-integration-tester.md` 的既有範例裡，但沒有明確寫成規範文字，之後若再犯可考慮補寫進那份規則檔案。
