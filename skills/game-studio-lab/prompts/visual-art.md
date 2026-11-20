# 任務: 視覺設計 — 「$element_name」的 3 個方案

這款遊戲要進打磨。使用者會在一頁方案頁上比較每個核心視覺元素的 3 個方案, 挑一個當打磨的方向。你這次只負責一個元素: **$element($element_name)**。

- 類型: $element_kind(static = 靜態, 畫一張; anim = 動態, 會播放)
- 內容: $element_content
- 為什麼是核心: $element_why
- 使用者對上一批的意見: $redo_note(「無」表示第一批)

## 請讀取
- `$visual_dir/elements.md` — 全部元素(知道其他元素在講什麼, 你的方案別跟它們重疊)
- 底版 `$base_dir/spec.md`、`$base_dir/game/art/style.md`、`$base_dir/game/art/art.js` — 遊戲現有的畫法與視覺語言
- `$studio_refs/art-lessons.md`

## 要做的事
在 `$visual_dir/options/` 寫:

1. `$element-A.js`、`$element-B.js`、`$element-C.js`, 每檔只定義一個物件:

```js
window.VISUAL_OPTION = {
  element: "$element", id: "A", kind: "$element_kind",
  size: [寬, 高],      // 依元素取景: 全畫面元素用遊戲畫布大小, 單一角色或特效可以小一點(例 480×360)
  duration: 秒數,       // 動態: 一次播放(或一圈循環)的長度; 靜態寫 0
  loop: true,           // 動態: 會不會循環
  draw(ctx, t) { ... }  // t = 秒; 每次呼叫都從頭畫完整一幀(頁面不會幫你清背景以外的東西)
};
```

   - 方案頁會先載入底版的 `art.js`(全域 `Art`), 再載入你的方案檔: 能用 `Art.xxx` 畫的就用, 新的畫法直接寫在方案檔裡; **不改** `art.js`
   - 只用 Canvas 2D, 不載入任何外部檔(圖片、字型、其他 js); 不碰 DOM、不用計時器, 動態完全由 t 決定(同一個 t 畫出同一幀)
   - **三個方案方向要明顯不同**: 構圖、造型語言、動態節奏或特效手法不同; 只換顏色或大小不算不同方向
   - 方案要是打磨真的做得出來的樣子: 挑中後會直接搬進遊戲當起點
   - 有使用者意見時, 這批照意見改方向
2. `$element.md`: 三行, 每行一句說明這個方案的方向差在哪, 給使用者看:
```
A: ...
B: ...
C: ...
```

**禁止啟動瀏覽器**(見共同守則)。用 Node vm + 假 canvas 載入 art.js 與三個方案檔, 對每個方案呼叫 draw(t=0、中間、結尾)自測不拋錯。

## 回報
三個方案各自的方向(各一句)、自測結果; 寫了哪條經驗提案(沒有就說無)。
