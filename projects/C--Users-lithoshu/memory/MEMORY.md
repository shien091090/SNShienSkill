# Memory Index

- [distill-me與output style位置](reference_distill_me_and_output_style.md) — 蒸餾工具裝在~/claude-distill-me；Lithoshu Voice output style在~/.claude/output-styles/lithoshu-voice.md

- [自動commit格式規則](feedback_auto_commit_format.md) — ⚠️任何commit前都要重新讀這份檔案全文再下手，不要只憑這行摘要或抄git log舊commit格式(曾因此連續寫錯submodule參照格式被糾正)
- [GAS 不自動 commit/push](feedback_no_auto_gas_commit.md) — gas_live_integration 的 git 操作一律由使用者自行執行
- [不自動 push（除更新GAS網址外）](feedback_no_auto_push_except_gas_url.md) — 修改後只 commit，不自動 push；push 需使用者明確指示
- [使用者語言偏好](user_language_preference.md) — 預設用繁體中文回覆，程式碼/路徑維持原樣
- [討論流程設計偏好純文字](feedback_prefer_open_text_over_askuserquestion.md) — 設計 skill/workflow 機制細節時避免用 AskUserQuestion 多選，改直接文字提問
- [分組日榜賽事頁 View 進度](dailyranktournament-match-view-progress.md) — 骨架程式碼已完成，待另開 session 用 Unity MCP 掛 prefab
- [不頻繁檢查編譯狀態](feedback_batch_compile_checks.md) — Unity開發時等測試+功能都寫完才一次確認編譯跑測試，不要每步都檢查
- [自動跑Test Runner與編譯](feedback_auto_run_test_and_compile.md) — 之後改完程式碼可直接用UnityMCP自動跑測試+確認編譯，測試全過就直接commit，不用先問
- [分組日榜拆解模塊進度](dailyranktournament-decompose-module-progress.md) — 28/29完成；HEAD e77a7166625(branch feature/Art_2607_DailyRankTournament，2026-08-13)；只剩FirstOpenTrigger待換手；已完成模塊仍常被要求回頭迭代行為細節；工作區持續有使用者並行編輯的DRT_SeasonTimeManager.cs等檔案維持不動
- [View顯示中文字一律走字表](feedback_display_text_via_localization.md) — Lobby專案不可寫死中文字串常數，找對應系統字表加Key後執行Convert選單；commit別漏帶LocalizationTableMap.asset
- [MVP Model架構規範位置](reference_mvp_model_architecture_rule.md) — aiToolLib rules/21-mvp-model-architecture.md，僅適用MVP架構(Guild/BattlePass/DailyRankTournament)，模塊依賴interface/命名/兩階段注入規則都在這
- [拆解模塊+迭代模塊已合併](reference_decompose_iterate_module_merge.md) — 單一模塊處理邏輯唯一權威在iterate-module，改細節只動這支不用動decompose-module
- [寫測試資料先查規則](feedback_check_unit_test_rules_before_copying_precedent.md) — memberId等固定格式欄位先查aiToolLib rules/14-unit-test.md，不要照抄同資料夾舊測試檔案
- [避免手動編輯prefab裡的TMP文字](feedback_avoid_hand_edit_prefab_tmp_text.md) — 直接改YAML的m_text可能觸發Unity重建TMP SubMeshUI，造成diff暴增；改用Editor/Inspector或提醒使用者手動處理，動完務必檢查diff規模是否合理
- [Tester參數名用中文](feedback_tester_param_name_chinese.md) — [TesterFunction]的customParameterName一律用中文,不要用英文欄位名,方便QA在Debug面板操作
- [808_Lobby_6000實際repo結構](reference_808_lobby_repo_structure.md) — 808_Lobby_6000本身就是主repo,Slot_Lobby沒有自己的.git;Tools/字表跟Slot_Lobby程式碼是同一repo可一起commit,只有ThirdParty/aiToolLib/各遊戲Scripts才是真submodule
