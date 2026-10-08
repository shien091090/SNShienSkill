# 任務: 音效修正($round_dir / $game)

接合腳本檢查沒過, 要由你修。

## 請讀取
- 修改方向: $fix
- 接合腳本的報告 `$report`
- `$game_dir/interface.json` 的 sounds / music
- `$game_dir/game/audio/` 下的 sound.js、sound.md、credits.md
- `$studio_refs/audio-lessons.md`

## 要做的事
只改 `game/audio/`, 讓 `window.Sound` 的 `init` / `play` / `playMusic` 存在且載入不拋錯, 事件名照 interface.json。換素材時照樣找免費授權並更新 credits.md。

## 回報
改了什麼、寫了哪條經驗提案(沒有就說無)。
