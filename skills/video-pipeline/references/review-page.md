# 審閱頁

`live/index.html` 發布成 Artifact。左邊每個有方案的關鍵幀一個分頁, 只有打開的分頁會建預覽(全部同時播會卡); 右邊是整支影片的播放器, 有秒數、拖曳進度、關鍵幀表格(按鈕開彈窗, 點一列跳過去)。使用者點方案 → 存進頁面資料庫 → 我讀。

## 每輪要改的地方(都在 index.html 的 script 開頭)

| 常數 | 內容 |
|---|---|
| `ROWS` | 這輪有方案的幀: `{ id:"k3", label:"K3 名稱", options:["0","a","b","c"], seg?:[從, 到] }`。和 film.js 的 OPTIONS 對齊 |
| `KF_DESC` | 每一幀 `[名稱, 一句話內容]`, 關鍵幀表格用。和 film.js 同步 |
| `FMT` | 預設 `undefined` = 主格式。要讓使用者看次要格式的版面時暫時設成 `"sq"` 或 `"por"` |

`ROWS` 空 + 有 `sfxopts.js` → 音效模式; 兩者都空 → 只有播放器。

## 發布

用到的檔案: `index.html` 是頁面, `film.js`、`gsap.min.js`、`sfxopts.js` 和 `sfx/*.wav` 走 `files`。

- 第一次發布: 先載入 `artifact-capabilities` skill, 再帶 `capabilities: {"db":{}}` 發布; 網址記進 STATUS.md
- 之後每輪: 同一個 `file_path` 重新發布(或在新 session 帶 `url`), 網址不變, 使用者的舊選擇也還在
- **一次發布最多 255 個檔案**。音效方案的 wav 很容易超過, 分幾次發布到同一個網址(後面的發布會疊加檔案)
- 換輪時把上一輪的音檔用 `null` 移掉, 不要讓檔案越積越多

## 讀使用者的選擇

用 ArtifactData 讀(網址 = 審閱頁):

| 文件 | 內容 |
|---|---|
| `picks/current` | 畫面方案 `{ "k3":"b", "k5":"0" }` |
| `sfx/current` | 音效方案, 每個音效時機選哪個 |
| `sfx/tune` | 音效微調 `{ 時機id: { db:+2, ms:-40 } }` |
| `music/current`、`music/tune` | 音樂方案與微調(音樂輪 `VID_DOC = "music"`) |

讀到後先用中文列給使用者核對再動手。沒選的幀 = 沒意見, 照 `"0"`(第 1 輪沒有 `"0"` → 問使用者那幀要哪個)。

## 音效、音樂模式

`sfxopts.js` 由音訊腳本產生:

```js
window.VID_SFX = [{ id, label, opts: [{ key, label, clips: [{ t, src }] }] }];
window.VID_BASE = { src: "sfx/base.wav", t: 0 };   // 音樂輪: 墊在底下的定案音效
window.VID_DOC = "music";                          // 音樂輪: 選擇存到 music/*
```

頁面用 Web Audio 對著播放器的時間排程播放, 選了方案就從該時機前 1.2 秒開始播。微調範圍: 音量 ±2 dB 一格(−12~+8), 時機 ±20 ms 一格(±200)。
