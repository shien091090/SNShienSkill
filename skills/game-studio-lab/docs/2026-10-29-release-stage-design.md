# game-studio-lab 發布階段設計

日期: 2026-10-29

## 目的

打磨完的遊戲要放上 PVD計畫網站(`E:\Project\PVDWebsite`)。網站對每款遊戲要的東西列在 `E:\Project\PVDWebsite\docs\素材清單.md`「一、每款遊戲」, 遊戲本身要守的規則在 `E:\Project\PVDWebsite\docs\遊戲接入規範.md`。發布階段把這兩份要求一次做齊, 產出一個可以直接交給網站的資料夾, 使用者不必另開 session 手動改遊戲、做素材。

網站上架的 4 款(使用者指定): 捕泡手(`E:\Project\Game\WebGame_BubbleCatcher`)、DungeonZoo(`E:\Project\Game\WebGame_DungeonZoo`)、GhostEchoV2(`E:\Project\Game\WebGame_GhostEchoV2`)、SoulSmithDefense(`E:\Project\Game\SoulSmithDefense`)。SlimeTetris 不上架。後三款是 lab 專案; 捕泡手是舊流程做的(無 `.lab/`、遊戲在根目錄 `game/`、無 `interface.json`、試玩紀錄是 `telemetry.md`), 要另有入口(見「非 lab 專案的發布」)。

成功的樣子: 使用者在打磨停下時選「發布」, 回答遊戲名稱與介紹, 等流程跑完, 看一張選擇頁挑圖示 / 主色 / 預覽圖, 回報代號, 拿到 `release/` 整包。

## 範圍

要做:
1. 遊戲執行檔: 打磨定版的複本, **移除一局結束下載試玩紀錄的機制**(含相關的暫存鍵, 例: DungeonZoo 的 `gamelog-...-pending`)
2. 發布素材: 素材清單「一、每款遊戲」的各項(見下表)

不做(使用者明確排除或之後再談):
- 手機版支援: 目前一律「只支援電腦」(`mobile: false`); 手機支援的發布流程等使用者實測 DungeonZoo 觸控版後再設計
- 接入規範的鍵名格式(`<代號>:<用途>`)、`pvd:pause` / `pvd:resume` 串接: 規範寫明可之後改, 這次不動
- 全站素材(網站標題、全站預覽圖、網站小圖示等)
- 把產物搬進 PVDWebsite repo, 或改網站的遊戲清單(名稱、代號、換掉 SlimeTetris): 素材資訊寫好即可, 網站由 PVD網站的工作另外更新

## 素材各項來源

| 項目 | 來源 | 說明 |
|---|---|---|
| 遊戲代號 | 主 session 帶預設, 使用者確認 | 預設依序取: 上次 `release/` 的值 → 網站 `E:\Project\PVDWebsite\site\js\games.js` 已定的值(`bubble-catcher`、`dungeon-zoo`、`ghost-echo`) → 由專案名推。上線後不改(這條是我的決定, 使用者沒否決) |
| 遊戲名稱 | **使用者提供** | 開發流程沒有定名步驟, 發布時由主 session 問。**名稱一旦定了要全部統一**: 遊戲開始畫面(打磨版與發布複本都改)、分享預覽圖、素材資訊都用同一個 |
| 遊戲介紹 | **使用者提供** | 1–2 句, 30–60 字; 主 session 收下時檢查字數, 超出就提醒(不代改) |
| 遊戲圖示 | 多方案挑選 | 512×512 PNG, 不透明背景; **只放角色 / 場景, 不放文字**; 重要內容在中間 80%(四角會被網站裁成圓角) |
| 遊戲主色 | 多方案挑選 | 一個色碼 + 主色上的字用深色或白色; 建議從 `#f29cac` 粉、`#aaefd5` 薄荷、`#4776c3` 藍、`#e0c64f` 金挑, 也可依遊戲配色另提 |
| 分享預覽圖 | 多方案挑選 | 1200×630 PNG; 角色與場景重新排版 **+ 遊戲名稱** |
| 遊玩時長 | 推算 | 從 `polish/logs/` 的試玩紀錄算一局時長, 寫成「X–Y 分鐘」; 沒紀錄就依關卡數與規格估, 並註明是估的 |
| 支援裝置 | 固定 | 「只支援電腦」 |
| 遊戲畫面比例 | 查程式 | 網站遊玩框是 21:9(1680×720); 發布時 RD 把橫式但比例不同的遊戲改成 21:9(網站版與打磨版都改, 設計區整塊置中、畫滿整面的東西延伸到兩側, 美術不拉伸), 畫布跟著容器等比縮放; 直式不改, 定版時在 `warnings` 提出。`info.json` 的 `ratio` 依實際比例填 |

操作方式說明不輸出: 網站不顯示, 操作由遊戲內教學帶(使用者決定)。

多方案的數量: 每項 3 個(圖示 A/B/C、主色 1/2/3、預覽圖 A/B/C)。

圖示與預覽圖的畫法: **沿用遊戲 `art/art.js` 裡已畫好的角色與場景重新排版**, 不生圖、不用實際遊玩截圖。

## 流程

### 進入

打磨停在 `waiting_feedback` 時, `--choice` 多一個 `release`(只有打磨階段有)。主 session 在訪談結尾問「再打磨、退回、結束, 還是發布」; 選發布前先問遊戲名稱與介紹, 寫成 `polish/release-info.md`, 用 `resume --choice release --feedback polish/release-info.md`。

選 `release` 不跑檢討假設(這輪若有試玩回饋要進設計, 應選 continue; 發布完回到同一個停點還能再選)。

### 發布節點(依序)

1. **遊戲複本 + 移除試玩紀錄**(RD): 把 `polish/game/` 複製成 `release/game/`(整個覆蓋舊的), 在複本上移除試玩紀錄下載與相關暫存鍵。`polish/game/` 不動, 下一輪打磨照樣有埋點。接合腳本要能跑過複本(腳本會讀上一層的 `interface.json`, 複本旁要放一份; 腳本本來就不檢查埋點, 不用放寬)
   - RD 改完後由程式清掉網站不要的檔: `.md`(授權來源 `audio/credits.md` 除外)與沒被 `index.html` 或其他程式提到的 `.js`(例: 美術參考用的 `ref-objects.js`)。網站同步工具照《遊戲發布格式》第二節檢查, 留著會被擋
   - 名稱與開始畫面現有名稱不同時, 開始畫面的名稱改成使用者給的(美術或 RD, 看名稱畫在哪), **打磨版 `polish/game/` 也一起改**, 下一輪打磨才不會變回舊名; 改完重跑接合腳本
2. **素材資訊**(一般 session): 推算時長寫成 `release/options/info.json`(或等價格式, 讓後面定版直接用)
3. **方案製作**(美術): 在 `release/options/` 做 3 張圖示、3 張預覽圖的繪製頁(引用 `release/game/art/art.js`), 與 3 組主色
4. **輸出 PNG**(程式, 非 AI): 用本機無頭 Chrome(`chrome --headless --screenshot --window-size=W,H`)把每張繪製頁存成 PNG。Chrome 不在時報錯停下
5. **選擇頁**(程式或美術): `release/options/index.html`, 只看不操作。並排列出:
   - 圖示 A/B/C: 原圖, 加一個裁成圓角 + 粗框的小尺寸預覽(模擬網站顯示 30–150 px)
   - 主色 1/2/3: 每組套在仿網站遊戲卡片上(主色底 + 該色字 + 遊戲名稱)
   - 預覽圖 A/B/C: 原尺寸縮放顯示
6. 停下, 狀態 `waiting_release_pick`, 回傳選擇頁絕對路徑

### 挑選與定版

使用者看選擇頁, 在對話告訴主 session 代號(例「圖示 B、主色 2、預覽圖 A」)。主 session 寫成 `polish/release-pick.md`, `resume --choice pick --feedback polish/release-pick.md`。

定版(程式): 把選中的檔案複製進 `release/assets/`, 寫 `release/assets/info.json`(網站同步工具讀的資料, 格式照 `E:\Project\PVDWebsite\docs\遊戲發布格式.md` 第三節)與 `release/assets/素材資訊.md`(給人看)。完成後回到打磨的 `waiting_feedback` 停點(同一版遊戲, 不重做), 使用者可再選 continue / back-* / end / release。

想換方案(例: 都不喜歡)→ 再選一次 `release` 重做方案。

### commit

跟其他停點一樣由 CLI 自動 commit + push, `release/` 整個在專案 repo 內。

## 非 lab 專案的發布(捕泡手)

捕泡手沒有進度檔, 進不了「打磨停下時選發布」。另開一條不依賴進度檔的發布指令(例 `release <資料夾> --info <檔>`), 跑同一組發布節點, 差別:
- 遊戲來源是 `<資料夾>/game/`; 開始畫面改名時改的是這份
- 試玩紀錄讀 `telemetry.md`(與其指向的檔), 推不出時長就估並註明
- 接合腳本需要的 `interface.json` 由發布節點依程式補一份放在 `release/` 底下(不寫回原專案根目錄)
- 產出一樣在 `<資料夾>/release/`, commit + push 到該資料夾自己的 repo(`shien091090/WebGame_BubbleCatcher`)
- 停在挑選頁、定版的方式與 lab 專案相同; 定版後流程結束(沒有打磨停點可回)

## 產出結構

```
<專案>/release/
├── game/                     遊戲執行檔(index.html 入口, 相對路徑, 無試玩紀錄下載)
├── assets/
│   ├── icon.png              512×512
│   ├── share.png             1200×630
│   ├── info.json             網站讀: code、name、intro、time、mobile、color、textColor、ratio
│   └── 素材資訊.md            同一份資料給人看(網站不讀)
├── interface.json            接合腳本讀(在 game/ 上一層), 網站不讀
└── options/                  所有方案、繪製頁、選擇頁(index.html), 網站不讀
```

## 限制

- 網站單一檔案不超過 25MB; 定版時檢查 `release/game/` 與 `assets/` 沒有超過的檔案, 有就在狀態 `warnings` 提出
- 發布節點的 `claude -p` 一樣用限縮工具(見 `lab/runner.py`), 不用 bypassPermissions
- 改 `lab/` / `check/` 後跑 pytest

## 留給實作者決定

- 新節點與狀態在 `lab/graph.py` / `lab/state.py` / `lab/cli.py` 的具體接法、新 prompt 檔命名
- 素材資訊的中間格式
- 選擇頁由程式模板產生或交給美術
- 主 session 的 SKILL.md 段落與 feedback 檔格式說明
