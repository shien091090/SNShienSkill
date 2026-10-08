# 任務: 音效($round_dir / $game)

## 請讀取
- `$game_dir/spec.md` 的「音效清單」
- `$game_dir/interface.json` 的 `sounds` / `music` — **事件名不可更改**, RD 正在同時照它呼叫
- `$studio_refs/audio-lessons.md`
- `$game_dir/game/audio/` 下既有的 sound.md、credits.md(有上一版才會有; 有就沿用素材與風格)

## 要做的事
產出 `$game_dir/game/audio/` 下的 `sound.js`、`sound.md`、`credits.md` 與 `assets/` 音檔。

- `window.Sound` 提供 `init()`、`play(事件名, opts)`、`playMusic(曲名)` 與靜音切換; 事件名照 interface.json
- 素材先從線上找免費授權資源(CC0 / 公有領域 / CC-BY 已署名 / 免署名可商用), 找不到合適的才用 Web Audio 程式產生
- 不用 CDN、不用 fetch 讀音檔(file:// 下會被擋); 音檔用 `<audio>` / `new Audio()` 的相對路徑或內嵌
- credits.md 每個音檔寫來源網址與授權
- 開工前讀經驗文件, 收工前依它的規則判斷要不要寫經驗提案到收件匣(見共同守則)

## 回報
每個事件用了哪個素材(或程式產生與理由)、授權統計、總檔案大小、寫了哪條經驗提案(沒有就說無)。
