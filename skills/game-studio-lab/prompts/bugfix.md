# 任務: 修試玩回報的 bug($round_dir / $game)

使用者試玩時回報了問題, 清單在 `$bugs`。

## 請讀取
- `$bugs`
- `$game_dir/spec.md`、`$game_dir/interface.json`、`$game_dir/guide.md`(探索 / 深掘才有)
- `$game_dir/game/` 下的程式; 美術交付 `game/art/style.md`
- `$studio_refs/rd-lessons.md`

## 要做的事
逐條找原因並修好。只改 `index.html` / `game.js` / `style.css`; 問題若出在美術(art/), 在回報裡說明, 不要自己改。用 Node vm 重現並驗證。修 bug 屬於「卡住又解掉」, 依經驗文件規則判斷要不要寫經驗提案到收件匣(見共同守則)。

## 回報
逐條: 原因、怎麼修、自測結果; 不能修的說明原因。
