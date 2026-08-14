---
name: dailyranktournament-match-view-progress
description: 分組日榜(DailyRankTournament)賽事頁 View 開發進度，下一步是用 Unity MCP 把腳本掛到 prefab 上
metadata: 
  node_type: memory
  type: project
  originSessionId: d8df64b6-5f67-447a-a8de-6b4146139fac
---

分組日榜活動系統（Slot_Lobby 專案，中文名「分組日榜」／英文名 DailyRankTournament）目前進度：

1. 已完成「轉換前端規格」skill，前端開發規格書在
   `Slot_Lobby\docs\開發文件與示意圖\活動系統\分組日榜(DailyRankTournament)\規格\DailyRankTournament_前端開發規格.md`
2. 已對「賽事頁」（賽事榜，非資格頁）跑完「示意圖轉view架構」skill（`parse-ui-mockup`），頁面正式命名為
   **分組日榜賽事頁 / DailyRankTournamentMatch**（不是 Eligibility，那是誤標的舊名）。
3. 骨架程式碼已寫入
   `Slot_Lobby\Assets\Scripts\Lobby\Activity\DailyRankTournament\Views\`：
   - `DailyRankTournamentMatchPanel.cs`（MonoBehaviour，非 ViewBehaviour）
   - `DailyRankTournamentMatchRankInfiniteCell.cs`
   - `RankScrollDisplayUnit.cs`
   - `IDailyRankTournamentMatchPanel.cs`
4. 互動式 Mockup HTML 在 `%TEMP%\DailyRankTournamentMatchMockup.html`（使用者已確認版面拆法）。

**下一步（待另開 session 執行）**：parse-ui-mockup skill 的 Step 6——用 Unity MCP 把 `DailyRankTournamentMatchPanel` 腳本掛到 prefab 上，並嘗試自動配對 Inspector 欄位。需要先向使用者詢問 prefab 路徑（例如 `Assets/Prefabs/Xxx.prefab`），使用者尚未提供。

**How to apply：** 新 session 若被要求「繼續掛 prefab」或「幫分組日榜掛腳本」，先讀取上述 4 個 .cs 檔案與 mockup html 確認欄位/function 清單，再依 `Skills/Lobby/UIParser/parse-ui-mockup/SKILL.md` 的 Step 6 流程執行，不需重新解析示意圖或重跑 Mockup 確認。
