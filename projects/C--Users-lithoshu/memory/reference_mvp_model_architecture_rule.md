---
name: reference-mvp-model-architecture-rule
description: Slot_Lobby 專案（aiToolLib）新增了 rules/21-mvp-model-architecture.md，MVP架構Model的模塊依賴/命名規則統一寫在這裡
metadata:
  node_type: memory
  type: reference
  originSessionId: 176f2d81-e077-4c2f-9332-ac215d7b56de
---

Slot_Lobby 專案的 `aiToolLib`（`D:\Git\808_Lobby_6000\aiToolLib\.claude\rules\21-mvp-model-architecture.md`，2026-07-17 新增）收錄了「MVP Model 架構規範」：模塊間依賴一律用 interface（不可具體類別）、介面命名規則（有系統前綴的類別 `I` 插在前綴後面，例如 `DRT_IQualificationTierSettings` 不是 `IDRT_QualificationTierSettings`）、`CreateModuleInstances()`/`InitializeModules()` 兩階段注入模式。

**適用範圍限制**：只適用於「Model 拆成多個職責單一子模塊、模塊間互相依賴」的 MVP 架構功能，專案內可參考 `GuildModel`、`BattlePassModel`（這兩個用建構子注入）、`DailyRankTournamentModel`（用新的兩階段模式）。**非 MVP 架構的舊功能（單一 Model 類別包辦所有邏輯）不適用**，不要為了套規則硬改既有架構。

原本這些規則寫在 `lobbyagents` 的 `Skills/Lobby/ActivityDev/activity-decompose-module/SKILL.md` 裡，2026-07-17 抽出來變成通用規則，該 skill 現在改為引用 `rules/21-mvp-model-architecture.md`，避免規則重複維護。詳見 [[dailyranktournament-decompose-module-progress]]。

**How to apply：** 之後任何 session 在處理 Guild/BattlePass/DailyRankTournament 這類 MVP 架構功能的模塊開發（不限於 activity-decompose-module skill 流程內），或使用者要求新增/修改模塊間依賴時，應先確認該功能是否為 MVP 架構，是的話直接查閱 `rules/21-mvp-model-architecture.md` 取得最新規則內容，不要用記憶裡的舊規則細節（規則本身可能持續更新）。
