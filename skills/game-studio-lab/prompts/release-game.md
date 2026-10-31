# 任務: 發布 — 網站版遊戲

這款遊戲要放上 PVD計畫網站。流程已把定版遊戲複製到 `$release_dir/game/`(網站版), 原本的遊戲在 `$src_dir/game/`。

- 遊戲名稱: $name
- 遊戲代號: $code

## 請讀取
- `$release_dir/game/` 下的 index.html、game.js、art/art.js
- `$src_dir/spec.md` 或 `$project/spec.md`(有哪份讀哪份)
- `$studio_refs/rd-lessons.md`
- `$studio_refs/touch-template.js`(觸控層範本, 第 6 步用)

## 要做的事
1. **移除試玩紀錄下載**(只改 `$release_dir/game/`): 網站版不能下載任何檔案到玩家電腦。拿掉一局結束下載試玩紀錄 JSON 的函式與所有呼叫點, 以及為它存在的東西(例: 沒下載完的紀錄暫存在 `gamelog-...` localStorage 鍵、補送機制、下載按鈕)。只用來產生紀錄的事件收集可以留著不呼叫或一起拿掉, 以不留死碼、不影響玩法為準。`$src_dir/game/` 的埋點**保留**, 之後的打磨還要用
2. **名稱統一**: 開始畫面顯示的遊戲名稱若不是「$name」, 把 `$release_dir/game/` **與** `$src_dir/game/` 兩份的開始畫面名稱都改成「$name」(含 `<title>`)。名稱畫在 art.js 時可以改 art.js 裡的標題文字與為了放下新名稱必要的字級 / 位置, 不改其他圖形; 名稱太長放不下就縮字級或換行, 不改名稱
3. **介面描述**: `$release_dir/interface.json` 不存在時, 依程式實際情況寫一份給接合腳本用, 格式:
   `{"canvas": {"width": W, "height": H}, "draw": [{"name": "drawXxx", "state": ["欄位", ...]}, ...], "sounds": ["音效名", ...], "music": ["音樂名", ...]}`
   `draw` 列出 game.js 呼叫的每個 `Art.drawXxx`, 且必須含 `drawTitle`(開始畫面)與 `drawTutorial`(新手教學提示); 遊戲沒有這兩個名稱時, 在 art.js 既有的開始畫面 / 教學繪製函式上加同名別名(只加別名, 不改圖)
4. **畫面改成 21:9**(PVD計畫網站的遊玩框是 21:9, 規範在 PVD計畫網站 repo 的 `docs/遊戲接入規範.md` 第四節第 3 點): interface.json 的 canvas 已經是 1680×720 就跳過這步。橫式但比例不同(例 1280×720、960×640)時, `$release_dir/game/` **與** `$src_dir/game/` 兩份都改成 1680×720, 兩份的 interface.json(`$release_dir/interface.json`, 以及 `$src_dir/interface.json` 有的話)canvas 與畫滿全畫面的 size 一起改:
   - 高度不同就先整體等比換算成高 720(座標、尺寸乘同一個倍數), 再處理寬度
   - 寬度不足 1680 的部分左右平均補: 原本的版面當成「設計區」整塊平移到中間(畫面最外層 translate 一次, 不逐一改座標), 只把**畫滿整個畫面**的東西(底色、背景、地面、暗角、壓暗、裁切範圍、全畫面特效)改成畫滿 1680; 場景往兩側延伸補畫, 美術不放大、不拉伸變形, 畫面不留空白或黑邊
   - 可視範圍跟著畫面寬的東西(捲動鏡頭、出界判斷、邊緣提示)改用新寬度; 地圖比畫面窄時置中並補牆或背景, 不露出地圖外
   - 已有觸控層(`touch.js`)時, 按鈕版面以畫布寬自動對齊, 不用搬; 原本為了避開按鈕而搬動的介面重新檢查還要不要搬
   - 不改玩法與數值: 遊戲區、判定範圍維持原大小
   - 直式畫面(高大於寬)不改, 在回報寫明「直式, 網站會加寬邊, 要改橫式需另外討論」
5. **畫布等比縮放**(兩份都查): 畫布要跟著容器(網站 iframe 或視窗)等比縮放並置中, 不裁切、不拉伸; 不假設視窗大小、不寫死畫布的 CSS 像素尺寸; 依 devicePixelRatio 放大實際像素, resize 與 orientationchange 時重算; 滑鼠 / 觸控座標用 `getBoundingClientRect` 換回邏輯座標。不符合就改
6. **觸控層與網站訊息**(兩份都做; 設計見 skill 的 `docs/2026-10-31-release-mobile-design.md`): 讓手機能玩, 並接上 PVD計畫網站的暫停 / 繼續 / 玩完一局訊息。
   - `touch.js` 不存在 → 把 `$studio_refs/touch-template.js` 原樣複製成 `$release_dir/game/touch.js` 與 `$src_dir/game/touch.js`, **只改開頭的 `CONFIG`**, 不改範本其他部分; 已存在(上一次發布加過)→ 保留, 只依這輪打磨的改動更新 `CONFIG`(新畫面、新按鍵)。兩份內容一致
   - `index.html` 在 `game.js` 之後載入 `touch.js`
   - `CONFIG.mode`: 鍵盤遊戲 `keys`; 滑鼠遊戲 `mouse`(點擊即觸控, 不畫按鈕; 遊戲聽 mouse / click 事件時 `mouseEvents: true`, 只聽 pointer 事件時 false); 直式遊戲 `none`(不做觸控, 只做網站訊息與 Esc 暫停)
   - `keys`: 方向鍵與 A(Z)/ B(X)/ 第三鍵(空白鍵)對應到 game.js 的鍵名, 遊戲用不到的鍵設 null; `keycaps`: 遊戲裡畫鍵帽時 fillText 的字(先 grep art.js 與 game.js 確認鍵帽字串, 例 'Z'、'空白'), 換成 A / B / 第三鍵圖示
   - `visible()`: 照 spec 的操作與場景, 每個畫面該顯示哪些按鈕。不能操作的畫面(自動翻頁、演出中)全部不畫; 只收某個鍵的畫面(例: 只能按 Z 繼續的引導卡)只畫那個鍵; 只在某場景有用的鍵在其他畫面不畫。按鈕會蓋住畫面邊緣的資訊: 對照美術與 game.js 的版位, 會被蓋住的資訊在觸控模式(`PVDX.on`)下由 RD 傳座標的移開, 美術固定版位的改成該畫面不畫那顆按鈕
   - `diagonal()`: 哪些畫面方向鍵可以斜走(角色自由移動的場景); `drawIcon`: 第三鍵圖示, 簡單幾何畫出該鍵的主要動作
   - `setAudioPaused(paused)`: 暫停時整個聲音靜音, 繼續時還原成遊戲自己的靜音設定(不動遊戲的靜音開關); `initAudio()`: 做遊戲第一次輸入時的聲音初始化
   - `escPause`: 遊戲自己沒有 Esc 暫停 → true(共同守則的通用鍵, 由觸控層提供); 已有 → false
   - game.js 掛鉤子(兩份): 鍵盤遊戲的鍵盤輸入要走全域 `inputDown(鍵名)` / `inputUp(鍵名)` / `inputReset()`(沒有就把現有的按鍵處理整理成這三個), `inputDown` 開頭 `if (window.PVDX && PVDX.paused) return;`; 每幀 `if (!(window.PVDX && PVDX.paused)) update(dt);`, 畫完 `if (window.PVDX) PVDX.draw(ctx);`; 一局結束的時間點(打磨版下載試玩紀錄的那一刻)呼叫 `if (window.PVDX) PVDX.finish();`
   - 手機不放任何聲音按鈕或暫停按鈕(靜音、音量交給手機本身)
7. 不改其他玩法、數值、美術、音效。不改存檔鍵名格式
8. 用 Node vm + 假 canvas 自測兩份遊戲載入與開局不拋錯, 並確認網站版找不到任何下載(`download`、`createObjectURL`、`a.click`)的呼叫; 觸控層用 `?touch=1` 等效的設定(假 location.search)載入, 確認 `PVDX.draw` 每個畫面都不拋錯、模擬 pvd:pause 後遊戲不前進

## 回報
移除了哪些東西、名稱改在哪(兩份都要寫)、有沒有寫 interface.json、畫面比例怎麼改(各畫面怎麼延伸、哪些畫滿整面的東西改了)、縮放怎麼做、觸控層設定(mode、各畫面顯示哪些按鈕、為了按鈕移開了哪些資訊、斜走的畫面、第三鍵圖示)、一局結束掛在哪、自測結果。
