# 任務: 發布 — 網站版遊戲

這款遊戲要放上 PVD計畫網站。流程已把定版遊戲複製到 `$release_dir/game/`(網站版), 原本的遊戲在 `$src_dir/game/`。

- 遊戲名稱: $name
- 遊戲代號: $code

## 請讀取
- `$release_dir/game/` 下的 index.html、game.js、art/art.js
- `$src_dir/spec.md` 或 `$project/spec.md`(有哪份讀哪份)
- `$studio_refs/rd-lessons.md`
- `$studio_refs/screen-width.md`(畫面寬度依裝置, 第 4 步用)
- `$studio_refs/touch-template.js`(觸控層範本, 第 6 步用)

## 要做的事
1. **移除試玩紀錄下載**(只改 `$release_dir/game/`): 網站版不能下載任何檔案到玩家電腦。拿掉一局結束下載試玩紀錄 JSON 的函式與所有呼叫點, 以及為它存在的東西(例: 沒下載完的紀錄暫存在 `gamelog-...` localStorage 鍵、補送機制、下載按鈕)。只用來產生紀錄的事件收集可以留著不呼叫或一起拿掉, 以不留死碼、不影響玩法為準。`$src_dir/game/` 的埋點**保留**, 之後的打磨還要用
2. **名稱統一**: 開始畫面顯示的遊戲名稱若不是「$name」, 把 `$release_dir/game/` **與** `$src_dir/game/` 兩份的開始畫面名稱都改成「$name」(含 `<title>`)。名稱畫在 art.js 時可以改 art.js 裡的標題文字與為了放下新名稱必要的字級 / 位置, 不改其他圖形; 名稱太長放不下就縮字級或換行, 不改名稱
3. **介面描述**: `$release_dir/interface.json` 不存在時, 依程式實際情況寫一份給接合腳本用, 格式:
   `{"canvas": {"width": W, "height": H}, "draw": [{"name": "drawXxx", "state": ["欄位", ...]}, ...], "sounds": ["音效名", ...], "music": ["音樂名", ...]}`
   `draw` 列出 game.js 呼叫的每個 `Art.drawXxx`, 且必須含 `drawTitle`(開始畫面)與 `drawTutorial`(新手教學提示); 遊戲沒有這兩個名稱時, 在 art.js 既有的開始畫面 / 教學繪製函式上加同名別名(只加別名, 不改圖)
4. **畫面寬度依裝置**(PVD計畫網站: 電腦遊玩框 16:9, 手機橫拿全螢幕; 做法與程式片段見 `$studio_refs/screen-width.md`): interface.json 的 canvas 已經是 `{"width": 1280, "height": 720, "maxWidth": 1680}` 且 art.js 已依裝置決定寬度就跳過這步。否則 `$release_dir/game/` **與** `$src_dir/game/` 兩份都改, 兩份的 interface.json(`$release_dir/interface.json`, 以及 `$src_dir/interface.json` 有的話)canvas 一起改:
   - 高度不同就先整體等比換算成高 720(座標、尺寸乘同一個倍數), 再處理寬度; 原本已是 1680×720 固定寬的, 版面若以 1280 設計區置中就直接改成依裝置, 若版面用滿 1680 就把重要內容收進中間 1280
   - 原本的版面當成「設計區」整塊平移到中間(畫面最外層 translate 一次, 不逐一改座標), 不縮小; 兩側多出來的寬度只在觸控模式出現, 由 `touch.js` 塗黑並放按鈕, 遊戲**不**往兩側延伸背景、壓暗或 HUD(見 `screen-width.md`)
   - 捲動鏡頭、出界判斷這類可視範圍維持設計區 1280 寬
   - 已有觸控層(`touch.js`)但版面是舊範本(按鈕疊在遊戲畫面上、兩側沒塗黑)時, 照新範本的版面段落與 `PVDX.draw` 開頭的塗黑更新; 原本為了避開按鈕而搬動的介面重新檢查還要不要搬
   - 不改玩法與數值: 遊戲區、判定範圍維持原大小
   - 直式畫面(高大於寬)不改, 在回報寫明「直式, 網站會加寬邊, 要改橫式需另外討論」
5. **畫布等比縮放**(兩份都查): 畫布要跟著容器(網站 iframe 或視窗)等比縮放並置中, 不裁切、不拉伸; 不假設視窗大小、不寫死畫布的 CSS 像素尺寸; 依 devicePixelRatio 放大實際像素, resize 與 orientationchange 時重算; 滑鼠 / 觸控座標用 `getBoundingClientRect` 換回邏輯座標。不符合就改
6. **觸控層與網站訊息**(兩份都做): 讓手機能玩, 並接上 PVD計畫網站的暫停 / 繼續 / 玩完一局訊息。
   - `touch.js` 不存在 → 把 `$studio_refs/touch-template.js` 原樣複製成 `$release_dir/game/touch.js` 與 `$src_dir/game/touch.js`, **只改開頭的 `CONFIG`**, 不改範本其他部分; 已存在(上一次發布加過)→ 保留, 只依這輪打磨的改動更新 `CONFIG`(新畫面、新按鍵)。兩份內容一致
   - `index.html` 在 `game.js` 之後載入 `touch.js`
   - `CONFIG.mode`: 鍵盤遊戲 `keys`; 滑鼠遊戲 `mouse`(點擊即觸控, 不畫按鈕; 遊戲聽 mouse / click 事件時 `mouseEvents: true`, 只聽 pointer 事件時 false); 直式遊戲 `none`(不做觸控, 只做網站訊息與 Esc 暫停)
   - `keys`: 方向鍵與 A(Z)/ B(X)/ 第三鍵(空白鍵)/ 功能鍵 d 對應到 game.js 的鍵名, 遊戲用不到的鍵設 null; 遊戲有電腦版靠額外按鍵開的功能(例: C 開圖鑑)就接到 d, `drawIconD` 畫該功能的圖示; B 與第三鍵永遠不會同時有用時設 `shareBC: true` 共用一格。`keycaps`: 遊戲裡畫鍵帽時 fillText 的字(先 grep art.js 與 game.js 確認鍵帽字串, 例 'Z'、'空白'), 換成 A / B / 第三鍵圖示
   - 鍵帽以外提到按鍵的字也要換: 純文字寫的「按 Z」「空白鍵」(教學泡泡、提示句)在觸控模式換成按鈕名; 手機沒有按鈕的鍵(Esc、M、沒接到 d 的功能鍵)的提示在 `PVDX.on` 時不畫
   - `visible()`: 照 spec 的操作與場景, 每個畫面該顯示哪些按鈕。不能操作的畫面(自動翻頁、演出中)全部不畫; 只收某個鍵的畫面(例: 只能按 Z 繼續的引導卡)只畫那個鍵; 只在某場景有用的鍵在其他畫面不畫。會疊在別的畫面上、要按鍵才關得掉的東西(引導卡、對話、確認框)**先判斷**, 再判斷「這個場景整組不畫」, 否則在不能操作的場景裡跳出來時沒有按鈕可按、玩家卡關; 自測逐一列出每個要按鍵才前進的狀態, 確認那時該畫的鍵都在。按鈕會蓋住畫面邊緣的資訊: 對照美術與 game.js 的版位, 會被蓋住的資訊在觸控模式(`PVDX.on`)下由 RD 傳座標的移開, 美術固定版位的改成該畫面不畫那顆按鈕
   - `diagonal()`: 哪些畫面方向鍵可以斜走(角色自由移動的場景); `drawIcon`: 第三鍵圖示, 簡單幾何畫出該鍵的主要動作
   - `setAudioPaused(paused)`: 暫停時整個聲音靜音, 繼續時還原成遊戲自己的靜音設定(不動遊戲的靜音開關); `initAudio()`: 做遊戲第一次輸入時的聲音初始化
   - `escPause`: 遊戲自己沒有 Esc 暫停 → true(共同守則的通用鍵, 由觸控層提供); 已有 → false
   - game.js 掛鉤子(兩份): 鍵盤遊戲的鍵盤輸入要走全域 `inputDown(鍵名)` / `inputUp(鍵名)` / `inputReset()`(沒有就把現有的按鍵處理整理成這三個), `inputDown` 開頭 `if (window.PVDX && PVDX.paused) return;`; 每幀 `if (!(window.PVDX && PVDX.paused)) update(dt);`, 畫完 `if (window.PVDX) PVDX.draw(ctx);`; 一局結束的時間點(打磨版下載試玩紀錄的那一刻)呼叫 `if (window.PVDX) PVDX.finish();`
   - 手機字級下限: 觸控模式下照 `$studio_refs/screen-width.md`「版面要顧的」的手機字級下限放大字與小圖示(art.js 與 game.js 兩份), 電腦版不動
   - 手機不放任何聲音按鈕或暫停按鈕(靜音、音量交給手機本身); 遊戲畫面上的聲音開關圖示在觸控模式(`PVDX.on`)不畫
7. **儲存與上層頁面**(兩份都改; 規範在 PVD計畫網站 repo 的 `docs/遊戲接入規範.md` 第一節與第四節第 4 點; 所有遊戲和網站共用同一份瀏覽器儲存):
   - localStorage / sessionStorage 鍵名一律改成 `$code:<用途>`(用途英文小駝峰, 例 `$code:best`、`$code:muted`), 不放版本號; IndexedDB 資料庫名同樣加 `$code:` 前綴, cookie 用 `${code}_`; 不用 `pvd:` 開頭(網站保留)
   - 改名要搬舊值: 讀新鍵沒有值時讀舊鍵, 有就寫進新鍵並刪掉舊鍵(只刪自己的舊鍵), 玩家的最高分、設定才不會歸零
   - 不呼叫 `localStorage.clear()` / `sessionStorage.clear()`, 不列舉刪除別人的鍵; 每個讀寫都包 try/catch, 儲存不能用(無痕、App 內建瀏覽器)時照樣能玩
   - 不碰上層頁面: 不用 `window.top` / `parent.location`、不改網址(`location.href =`、`assign`、`replace`、`reload`)、不開新視窗(`window.open`)。只有觸控層送給網站的 postMessage 可以碰 `window.parent`
   - 沒用到儲存、也沒有這些寫法就跳過
8. 不改其他玩法、數值、美術、音效
9. 用 Node vm + 假 canvas 自測兩份遊戲載入與開局不拋錯, 並確認網站版找不到任何下載(`download`、`createObjectURL`、`a.click`)的呼叫; grep 兩份確認儲存鍵名都是 `$code:` 開頭、沒有 `.clear(`、`window.top`、`window.open`、改網址的寫法; 觸控層用 `?touch=1` 等效的設定(假 location.search)載入, 確認 `PVDX.draw` 每個畫面都不拋錯、模擬 pvd:pause 後遊戲不前進

## 回報
移除了哪些東西、名稱改在哪(兩份都要寫)、有沒有寫 interface.json、畫面比例怎麼改(設計區怎麼置中、觸控層版面有沒有更新)、縮放怎麼做、觸控層設定(mode、各畫面顯示哪些按鈕、為了按鈕移開了哪些資訊、斜走的畫面、第三鍵圖示)、一局結束掛在哪、儲存鍵名改了哪些(舊名 → 新名, 怎麼搬舊值)與拿掉的上層頁面寫法、自測結果。
