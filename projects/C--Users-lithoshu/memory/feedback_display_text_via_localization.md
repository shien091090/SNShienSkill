---
name: feedback-display-text-via-localization
description: Lobby專案(Slot_Lobby)開發時，任何要讓View顯示的中文字一律走字表，不可寫死字串常數
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1cacd1f7-cde5-46f9-9520-7acea78d15e2
  modified: 2026-08-11T01:15:46.288Z
---

實作 Lobby 專案功能時，只要程式碼會讓 View 顯示中文字（狀態文字、提示文案、格式化文字的固定部分等），一律不能寫死字串常數（例如 `public const string XXX = "本場剩餘";`），必須走字表流程。

**Why：** 2026-07-26 在 `DRT_MatchPageViewPresenter` 實作時，把「本場剩餘」「賽事已結束」「賽號」三個顯示文字直接寫成 `DRT_Const.cs` 裡的字串常數，被使用者發現這樣不對，要求改走字表（見 [[dailyranktournament-decompose-module-progress]]）。專案本身有完整的多語言字表機制（`rules/15-localization.md`），寫死字串會繞過這套機制，之後企畫要改文案或要做真正多語言時會漏掉。

**How to apply：**
1. 找到對應系統的專用字表檔案（`{父層資料夾}\Tools\Math_Data\~Localization\`，例如分組日榜對應 `daily_rank_tournament_ui_localize.xlsx`），沒有專用檔案才退回 `ui_localize.xlsx`
2. 用該目錄下的 `add_localization_key.py` 新增 Key，Const 類別只存 `LOCALIZE_KEY_...` 常數（存 key 字串，不存中文內容本身）
3. production code 一律透過 `IDataTableManager.GetText(key)` 取得文字，沒有這個依賴就補上
4. 新增完字表後執行 Unity Editor 選單 `LobbyTools/Localization/Convert All xlsx to Localization (多語系)`——這個選單 RPC 常逾時/斷線但背景仍會執行完成，不要重複觸發疊加執行，改為等待後直接檢查 `Assets/SourceFiles/Localization/{檔名}_zh-TW.asset` 內容（用 `{檔名} Shared Data.asset` 裡的 `m_Key`/`m_Id` 對照）確認轉換結果
5. **⚠️ commit時容易漏掉 `Assets/SourceFiles/LocalizationCommon/ScriptableObject/LocalizationTableMap.asset`**：這份檔案記錄每個Key屬於哪個table檔案（`key`→`tableName`對照），新增字表Key時這份檔案也會被Convert選單一起更新，是這次改動的必要部分（不是Unity重新序列化的無關噪音），commit時要用 `git diff` 確認裡面真的有新增的 Key 對照才確定要不要包含——2026-08-11 就曾在第一次commit時漏帶這份檔案，被使用者發現後才補commit

這條規則已經寫進 `lobby-agent-client` 的 `Skills/Lobby/ActivityDev/activity-iterate-module/SKILL.md` 通用規則區塊，走 iterate-module/decompose-module 流程時 skill 本身就會提醒；但若在該流程之外（例如使用者直接要求改某個 View 文字）也要主動套用這條規則。
