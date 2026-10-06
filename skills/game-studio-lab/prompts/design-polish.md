# 任務: 打磨階段設計(第 $round_no 輪, 產出到 `$round_dir/game/`)

你是遊戲設計師。玩法已經定案, 打磨階段只做**一款**, 讓它成為完整的小遊戲: 有關卡、難度曲線、音效。

## 請讀取
- `$project/idea.md`、`$project/hypotheses.md`
- 上一輪的回饋 `$project/$prev_round/feedback.md`
- 底版: 上一輪是深掘 → 回饋與驗證文件指出的勝出款; 上一輪是打磨 → `$project/$prev_round/game/`。讀它的 spec.md、interface.json、guide.md
- 上一輪的試玩紀錄 `$project/$prev_round/logs/`(有的話)與難度分析 `$project/$prev_round/difficulty.md`(有的話)
- `$studio_refs/guide-principles.md`

## 要做的事

1. 以底版為基礎(沿用它的規則與 interface.json, 只做必要增修), 寫 `$project/$round_dir/game/` 下的三個檔
2. 把底版遊戲的 `game/art/` 複製到 `$project/$round_dir/game/game/art/`, 美術會在上面修改而不是重畫
3. spec.md 在探索 / 深掘的章節之外, 加三章:
   - `## 關卡`: 關卡數與每關的參數(表格), 難度怎麼爬升
   - `## 埋點`: 每局結束自動下載 JSON(檔名 `gamelog-<專案資料夾名>-<YYYYMMDD-HHMMSS>.json`), 列出事件與欄位; 至少能算出每關通過時間、失敗次數、卡關位置
   - `## 音效清單`: | 事件 | 何時發生 | 要讓玩家感覺到什麼 |, 另列背景音樂與靜音操作(同一種輸入)
4. interface.json 加 `"sounds": [事件名...]` 與 `"music": [曲名...]`; 新增物件照規則補 draw 函式
5. 回饋若有難度意見, 調整關卡參數; 在 `$project/hypotheses.md` 修訂紀錄加一行說明本輪改了什麼

## 回報
底版是哪款、關卡數、埋點事件、音效清單、相對底版改了什麼。
