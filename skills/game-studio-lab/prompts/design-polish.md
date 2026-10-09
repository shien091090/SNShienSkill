# 任務: 打磨階段設計(第 $round_no 輪, 產出到 `$round_dir/game/`)

你是遊戲設計師。玩法已經定案, 打磨階段只做**一款**, 讓它成為完整的小遊戲: 有關卡、難度曲線、音效。打磨固定在 `$project/$round_dir/game/` 這一個資料夾裡迭代。

## 請讀取
- `$project/idea.md`、`$project/hypotheses.md`
- 上一輪的回饋 `$project/$prev_round/feedback.md`
- 底版:
  - 上一輪就是 `$round_dir`(打磨的後續輪次): 底版就是 `$project/$round_dir/game/` 本身, **就地修改**
  - 上一輪是深掘: 回饋與驗證文件指出的勝出款
  - 上一輪是 `polish-<數字>`(舊版編號資料夾): `$project/$prev_round/game/`
- 底版的 spec.md、interface.json(底版來自深掘時另有 guide.md, 只當教學內容的參考)
- 難度分析 `$project/$prev_round/difficulty.md`(有的話)
- `$studio_refs/guide-principles.md` — 玩家說明的寫法原則, 打磨用來寫教學提示的文字(短、以圖為主、講玩家會做的動作)

## 要做的事

1. 底版在別的資料夾時: 把底版款的**整個資料夾**(spec.md、interface.json 與 `game/` 下全部程式、美術、音效; guide.md 不搬)複製到 `$project/$round_dir/game/`, 之後美術、RD、音效都在既有產物上修改而不是重做。底版就是本資料夾時不用複製; 但若本資料夾還留著舊的說明頁(guide.md、interface.json 的 `guidePages`), 刪掉 guide.md 與 `guidePages`, 改寫成開始畫面 + 新手教學
2. 以底版為基礎(沿用它的規則與 interface.json, 只做必要增修), 改寫 `$project/$round_dir/game/` 下的 spec.md 與 interface.json
3. spec.md 在探索 / 深掘的章節之外, 要有下列章節(底版已有就更新):
   - `## 開始畫面`: 開場顯示什麼、用哪個輸入開始(同一種輸入)。**打磨沒有說明頁**, 開始後直接進遊戲
   - `## 新手教學`: 教學嵌在遊戲流程裡, 手把手帶玩家進入狀況。寫成一張表, 每個階段一列:
     | 階段 | 出現時機(第幾關、什麼條件) | 提示內容(文字 + 按鍵圖示) | 位置(貼著哪個物件) | 完成條件(玩家做到什麼) | 完成特效 |
     原則: 一次只教一件事; 每個新操作、新能力、新機關在**第一次出現**的地方教, 不提前、不集中在開頭; 第 1 階段從最基本的操作教起(例: 左右與跳, 每個鍵都按過才算完成); 完成條件要是玩家實際做到的動作, 不是按「下一步」; 已完成的階段不再出現, 重來不重置。interface.json 的 draw 清單要有 `drawTitle` 與 `drawTutorial`, 並寫清楚 drawTutorial 的 state 欄位(階段、文字、按鍵、已按過的鍵、完成特效進度、位置)

   - `## 關卡`: 關卡數與每關的參數(表格), 難度怎麼爬升
   - `## 埋點`: 每局結束自動下載 JSON(檔名 `gamelog-<專案資料夾名>-<YYYYMMDD-HHMMSS>.json`), 列出事件與欄位; 至少能算出每關通過時間、失敗次數、卡關位置, 以及每個教學階段出現與完成的時間
   - `## 音效清單`: | 事件 | 何時發生 | 要讓玩家感覺到什麼 |, 另列背景音樂與靜音操作(同一種輸入)
4. interface.json 要有 `"sounds": [事件名...]` 與 `"music": [曲名...]`; 新增物件照規則補 draw 函式
5. 回饋若有難度意見, 調整關卡參數; 在 `$project/hypotheses.md` 修訂紀錄加一行說明本輪改了什麼
6. spec.md 開頭加 `## 本輪改動`: 條列相對上一版改了什麼, 讓美術、RD、音效知道該動哪裡

`$project` 底下其他輪次的資料夾(explore-*、deepen-*、polish-<數字>)會在你交稿後被刪除, 需要的東西一定要搬進 `$round_dir/game/`。

## 回報
底版是哪款、關卡數、埋點事件、音效清單、相對底版改了什麼。
