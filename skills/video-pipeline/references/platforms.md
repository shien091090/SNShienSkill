# 平台規格

## 平台 → 格式

| 平台 | `picks.fmt` | 尺寸 | 構圖重點 |
|---|---|---|---|
| IG(貼文、Reels 都一樣, 使用者指定的特規) | `sq` | 1080×1080 | 個人頁格狀把 1:1 裁成 3:4, 左右各少 135 px; 文字與主角放在中間 810 px 寬內 |
| Threads、TikTok、YT Shorts、網站、其他 | `por` | 1080×1920 | 平台介面蓋住上方約 220 px、下方約 400 px、右側約 160 px; 文字與主角放在 x 60~920、y 220~1520 |

使用者之後若改了某平台的比例, 改這張表與 `SKILL.md` 的平台表, 兩處一起改。

安全區只是估計值(各平台改版會變), 留餘裕比剛好貼齊好。

## 編碼(所有格式共用, `tools/renderfilm.mjs` + `tools/finish.mjs` 已照此實作)

- MP4、H.264 High、yuv420p、30 fps、CRF 16、`+faststart`(網頁邊下載邊播)
- **BT.709 有限範圍並加標記**。截圖是全範圍 BT.601, 不轉不標的話瀏覽器會顯示得偏飽和(實例: #f5e291 變 #fff193)
- 音訊 AAC 256k、48 kHz

## 音量

| 用途 | 響度 | 峰值 |
|---|---|---|
| 社群(IG、Threads、TikTok、Shorts) | −14 LUFS | −1 dBTP |
| 網站自動播放 | −16 LUFS | −1 dBTP |

網站的影片自動播放時一定是靜音, 畫面要在沒有聲音時也看得懂。

`node tools/finish.mjs <無聲畫面.mp4> <音軌.wav> <輸出.mp4> -14 -1` 做兩階段響度正規化 + 合成 + 檢查, 有一項不過就 exit 1。

## 封面圖

IG 與 Threads 都會用到。從定案影片截一格(使用者挑), 存成 `output/<片名>-<平台>-cover.jpg`, 尺寸同影片:

```bash
"$FFMPEG" -ss <秒> -i output/<片名>-<平台>.mp4 -frames:v 1 -q:v 2 output/<片名>-<平台>-cover.jpg
```
