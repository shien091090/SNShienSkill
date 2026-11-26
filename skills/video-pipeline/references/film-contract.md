# film.js 寫法

`live/film.js` 是整支影片, 一條 GSAP 時間軸。審閱頁(index.html)、渲染(test.html + tools/*.mjs)都靠下面這組約定, 改的時候不要破壞它。範本本身就是一個能跑的最小例子, 從它長出來。

## 約定

| 名稱 | 內容 |
|---|---|
| `FORMATS` | `{ sq:{W,H}, por:{W,H}, wide:{W,H} }`, 只留這支影片要出的; 第一個是主格式。`picks.fmt` 選格式 |
| `KEYFRAMES` | `[id, 開始, 長度]`, 1 倍速秒數。id 用 `k1`、`k2`…, 中途插入新幀時用 `k5b` 之類, 不要整批重新編號(使用者的選擇與 log 都靠 id) |
| `OPTIONS` | 這一輪有方案的幀: `{ k3:["0","a","b","c"] }`。`"0"` = 目前的基準(第 1 輪沒有基準, 只有 a~d)。沒在清單裡的值一律當 `"0"` |
| `DUR(pick)` | 依選擇改某幀長度, 例 `{ k5: pick("k5")==="b" ? 2.4 : 2.0 }` |
| `SPEED` | 全片倍速。整體太慢先調這個, 再個別調幀 |
| `CSS` | 字串, 所有規則加 `.vid` 前綴(一頁有很多支影片) |
| `fontsFor(picks)` / `FONT_SAMPLE` | 要先載入的字型; `FONT_SAMPLE` 要包含片中所有特殊字(子集字型只載這些字) |
| `build(host, picks)` | 回傳 `{ tl, total, starts, durs, film, sfx }`, 時間都已除以 SPEED |
| `cue(kind, t, {id})` | 在造成聲音的畫面事件旁登記音效時機, 第 1 輪就要放(之後拆音效方案靠它) |

每幀一個區塊:

```js
// ===== K3 · 名稱 =====
{
  const s = starts.k3, k = pick("k3");
  if (k === "b") { /* 方案 b */ }
  else if (k === "c") { /* 方案 c */ }
  else { /* "0" 或 a: 基準 */ }
}
```

使用者選完 → 把選中的分支留下當唯一寫法, 刪掉其他分支, 從 OPTIONS 移除。

## 尺寸

位置與字級都從 `L = size(picks)` 算(`L.W * 0.1`), 不寫死像素, 兩種格式才能共用時間軸。兩種格式構圖差太多時(例如直式要直排標題、格狀改 2 欄 4 列), 用 `fmtOf(picks)` 分支, 不要另開一份 film.js。

## 踩過的坑

- **`fromTo` 一律用範本裡的 `fromTo()` 包裝, 不直接呼叫 `tl.fromTo`**: 包裝會加 `immediateRender:false`, 並把「只寫在起點、終點沒寫」的屬性(典型是 `{autoAlpha:1, scale:0}` → `{scale:1}` 這種用起點來顯示元素的寫法)補進終點。不補的話第一次播放正常, 審閱頁循環重播後元素會一直隱藏(掉圖)
- **同一個元素、同一個屬性, 同一時間點只能 set 一次**。「先全部隱藏、再顯示其中一個」寫成兩個 `tl.set(…, 0)` 時, 重播不會重套第二個 → 拆成 `others` 與 `one` 各 set 一次。關鍵幀從 0 秒開始時, 它的 set 和初始狀態撞在同一刻, 時間加 0.001
- 起始狀態用 `tl.set(…, 0)` 明確設定; 每個會動的屬性都要有明確的起點, 影片循環回 0 時才會一樣。例外: SVG 線條「還沒畫出來」的 `strokeDasharray/strokeDashoffset` 直接寫進元素 style, 不用 set at 0(循環回 0 時會被撤銷, 前方的線會先整條閃出來)
- **進場動畫開始前, 元素要已經是隱藏姿勢**: 一幕裡多個元素依序進場(錯開 0.07 秒、0.3 秒…)時, 在這幕開頭就把每個元素 set 成起始姿勢(縮成 0、移到畫面外), 再用 `tl.to` 進場。只靠各自延後開始的 `fromTo`, 等待的那段時間元素會以完整樣子先出現一下(閃爍、對不齊)
- 上面兩條第一次播放都看不出來, 發布前用 `node tools/replaycheck.mjs '<picks>'` 模擬「播完 → 跳回 0 → 再播」比對畫面, 每組方案(全 a、全 b、全 c…)各跑一次
- 圖片一律用 `<img>`(放 `live/img/`, 用相對路徑 `img/x.png`), 不用 CSS `background-image`: 渲染器只等 `<img>` 解碼完才開始截圖, 背景圖會在前幾格缺圖
- **字型先載入再 build**: 文字在 build 時量尺寸, 字型沒到會整個跑位。Google Fonts 用 `display=block`
- **頁面隱藏時量到的尺寸全是 0**: 審閱頁已處理(等 ResizeObserver 有寬度才 build), 自己寫量測時記得
- `preserve-3d` 的父層設 opacity 會把 3D 壓平, 要淡出就淡它的子元素
- 3D 牆面上的位置: 先擺好姿勢用 `getBoundingClientRect` 量, 再還原
- 要用 three.js 時: 用一個代理 tween 的 `onUpdate` 呼叫 `render(t)`, 讓 GSAP 時間軸驅動, 渲染工具才能逐格 seek
- 時間軸只能靠 `tl.seek(t)` 推進, 不能用 `setTimeout`、CSS animation、`requestAnimationFrame` 自己跑的動畫(逐格渲染抓不到)

## 自己檢查

```bash
node tools/shot.mjs '{"k3":"b"}' renders/k3b 2.0 2.4 2.8      # 截幾格看
node tools/renderfilm.mjs '{"k3":"b"}' renders/check.mp4 30    # 需要看動態時
```

發布前每個新方案至少截 2 格看過: 構圖在安全區內、文字沒溢出、沒有元素殘留在不該出現的地方。

- 從主視覺裁下來的圖塊(含底色)疊在自畫色塊上時, 分隔線要放在圖塊之上, 否則圖塊邊緣會吃掉線。把原圖延伸出去的色塊, 斜率與位置要從原圖量(掃像素找線), 推近時對「原圖 + 延伸色塊」整層縮放, 只縮原圖會錯開。

- 某一段改用 Motion Canvas 做: 在片名資料夾開 `mc/`(Motion Canvas 3.x + vite), 用無頭 Chrome 開編輯器按 Render 輸出 PNG 序列, 轉成 JPG 後由外掛方案逐格切換顯示(每格 `tl.set` 顯示/隱藏, 時間提前 0.001 秒)。坑: vite plugin 在 `"type": "module"` 下要取 `.default`; 多專案網址是 `/src/<名>`; 大的 `shadowBlur` 會讓其他節點畫不見, 改用疊半透明形狀; `scaleX` 要用 `scale.x(...)` 做補間; 重新算圖前先刪掉舊輸出資料夾。審閱頁一次發布最多 255 個檔, 畫格要分批發布。

## 遊戲片段

遊戲實機畫面(`game-capture.md`)放進時間軸的做法, 實例是 `reference-impl/film/game-clips-film.js`(接力吉尼介紹影片的 film.js, 讀來參考, 裡面的幀與片段都是那支影片的):

- 每個畫面位置一個 `<canvas>`, 用「片段表」記錄每個時間區間畫哪個片段的第幾格(`seg(畫布, 片段, 起格, 迄格, 起秒, 迄秒)`; 多段接起來用同一速度鋪滿)。慢動作 = 同一段格數鋪更長的時間, 所以素材要 60fps 才不卡
- 渲染時(`test.html` 設 `window.VID_RENDER = true`)直接畫原始畫格 JPG; 審閱頁畫格太多不能發布, 改用壓成全關鍵格(`-g 1`)、640 寬的 `live/clips/*.mp4` 逐格 seek
- 審閱頁的片段**開頁就整支下載成 blob**, 下載完才開始播: film.js 設 `window.VID_CLIPS = { ready, progress }`, 樣板 `index.html` 看到它就蓋一層「載入遊戲畫面 n / N」、等 `ready` 才建影片並從頭播(寫法見實例)。只設 `v.src = "clips/x.mp4"` 邊播邊下載, 第一次播全黑, 快閃段每段換片段時跳格跟不上、停在舊畫面或角色消失, 重播幾次被瀏覽器存起來才慢慢好——本機 `file://` 的檢查完全看不出來
- `seeked` 時先把已跳到的那一格畫上, 再判斷要不要追跳到最新目標; 等完全對上才畫, 即時播放時目標一直往前, 畫面就一直不更新。畫之前只比對「畫布還停在這個片段」, 不比對格數
- 主播放器可提供 `FILM.warm()`: 建好每段要用的影片並跳到該段開頭, 第一次播到不用臨時建
- 畫格是非同步載入的: film.js 要提供 `FILM.settle()`, 等這一格要畫的圖都畫好才回傳。`renderfilm`、`shot`、`replaycheck` 每次 seek 後都會等它, 沒提供就不等
- 鏡頭(放大、平移)用包住畫布的元素做 transform, 並夾住不露出片段邊緣; 放大超過 1 倍的段落, 素材要用 2 倍解析度錄
- 遊戲音效: 錄影時記下的音效事件(`events.json`/`.sfx.json`)換算成影片時間, 在同一刻放 `cue()`, 聲音階段就能用遊戲原音精準對齊

