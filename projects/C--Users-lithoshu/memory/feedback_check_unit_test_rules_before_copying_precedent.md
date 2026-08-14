---
name: feedback_check_unit_test_rules_before_copying_precedent
description: 寫Lobby單元測試資料格式(如memberId)時，先查aiToolLib rules/14-unit-test.md規範，不要憑感覺照抄同資料夾裡任一既有測試檔案
metadata: 
  node_type: memory
  type: feedback
  originSessionId: fb9b4e46-4cd7-488a-a19c-095c2d96cd97
  modified: 2026-08-04T02:59:23.744Z
---

寫測試資料（尤其是有固定格式的欄位，如 `memberId`）時，第一步應該去查 `aiToolLib/.claude/rules/14-unit-test.md`，而不是隨便挑同資料夾裡一個既有測試檔案照抄格式。

**Why:** 在 [[dailyranktournament-decompose-module-progress]] 的 `DRT_SeasonRankingManagerTest.cs` 案例中，`memberId` 測試資料先寫成 `"M1"/"Self"`，被使用者糾正後又照抄了 `DRT_MatchRankingManagerTest.cs` 的舊寫法（`"P001"/"SELF"`），結果**兩次都錯**——正確規則其實是 `rules/14-unit-test.md` 明文規定的 `"JCG"+10位數字` 格式。那份舊測試檔案是在規則訂立之前寫的，不能當作可靠的規則來源，只是恰好也在同一個目錄底下。

**How to apply:** 之後在 Lobby 專案寫任何新測試檔案，遇到需要決定測試資料格式（memberId、時間戳、金額欄位等）時，優先查閱對應的 aiToolLib rules 文件（尤其是 `rules/14-unit-test.md`），而不是「看隔壁測試檔案怎麼寫就跟著寫」。若手邊沒有明確規則可查，才退而參考同類型模塊的既有測試檔案，並留意該檔案的建立時間是否早於規則制定。
