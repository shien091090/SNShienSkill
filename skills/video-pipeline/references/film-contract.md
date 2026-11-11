# film.js 寫法

`live/film.js` 是整支影片, 一條 GSAP 時間軸。審閱頁(index.html)、渲染(test.html + tools/*.mjs)都靠下面這組約定, 改的時候不要破壞它。範本本身就是一個能跑的最小例子, 從它長出來。

## 約定

| 名稱 | 內容 |
|---|---|
| `FORMATS` | `{ sq:{W,H}, por:{W,H} }`, 只留這支影片要出的; 第一個是主格式。`picks.fmt` 選格式 |
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

- **`fromTo` 要加 `immediateRender:false`**, 起始狀態用 `tl.set(…, 0)` 明確設定。不然往回拖、循環播放時會顯示錯的值
- 每個會動的屬性都要有明確的起點, 影片循環回 0 時才會一樣
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
