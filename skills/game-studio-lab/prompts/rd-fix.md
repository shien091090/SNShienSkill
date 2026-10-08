# 任務: RD 修正($round_dir / $game)

接合腳本檢查沒過, 要由你修。

## 請讀取
- 修改方向: $fix
- 接合腳本的報告 `$report`
- `$game_dir/interface.json`、`$game_dir/spec.md`
- `$game_dir/game/` 下的 index.html、game.js; 美術交付 `game/art/style.md`(只讀, 不改 art/)
- `$studio_refs/rd-lessons.md`

## 要做的事
只改 `index.html` / `game.js` / `style.css`, 讓報告裡的錯誤消失, 不改規格行為。用 Node vm 載入 art.js 與 game.js 自測。踩到跨遊戲通用的坑就依經驗文件規則寫一條經驗提案到收件匣(見共同守則)。

## 回報
改了什麼、自測結果、寫了哪條經驗提案(沒有就說無)。
