# 任務: 美術修正($round_dir / $game)

接合腳本檢查沒過, 錯誤判定認為要由你修。

## 請讀取
- 錯誤判定給你的修改方向: $fix
- 接合腳本的報告 `$report`
- `$game_dir/interface.json`(繪圖介面, 不可更改)
- `$game_dir/game/art/art.js`、`$game_dir/game/art/style.md`
- `$studio_refs/art-lessons.md`

## 要做的事
只修 `game/art/` 下的兩個檔, 讓它符合 interface.json 且不拋錯。不改函式名與參數(除非就是函式名寫錯)。修完用 Node 以假 ctx 呼叫每個匯出函式自測。若這次踩到的是「下次別的遊戲也會踩」的坑, 依經驗文件規則回寫(先重讀再改)。

## 回報
改了什麼、自測結果、回寫了哪條經驗(沒有就說無)。
