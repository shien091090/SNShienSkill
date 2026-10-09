# 任務: 美術($round_dir / $game)

## 請讀取
- `$game_dir/spec.md`、`$game_dir/guide.md`(探索 / 深掘才有)
- `$game_dir/interface.json` — **繪圖介面, 不可更改**
- `$studio_refs/art-lessons.md` — 美術經驗文件(設計理念與經驗兩層)
- `$game_dir/game/art/style.md` 與 `art.js`(打磨階段才會有, 是上一版的美術; 有就沿用它的視覺語言, 只改規格變動牽涉的物件)

## 要做的事
產出 `$game_dir/game/art/art.js` 與 `$game_dir/game/art/style.md`。

- RD 正在**同時**照 interface.json 寫遊戲, 不會等你: 函式名、參數、state 欄位一律照 interface.json, 一個不多一個不少
- `window.Art.canvas` 必須等於 interface.json 的 canvas 寬高
- 每個物件畫在 interface.json 的 `size` 範圍內(那是判定範圍, 畫面邊界要等於判定邊界)
- **探索 / 深掘(說明頁)**: 另做 `drawGuidePage(ctx, state)`, state 為 `{ page, x, y, w, h }`(page 0 起算), 畫 guide.md 每頁「圖要示意什麼」; 圖裡的遊戲物件直接用遊戲內的畫法
- **打磨(沒有說明頁)**: 照 interface.json 做 `drawTitle`(開始畫面: 遊戲名、開始提示)與 `drawTutorial`(嵌入式新手教學提示, 照 spec「新手教學」表的提示內容與位置)。教學提示的**文字、按鍵圖示、已按過的鍵的打勾或變色、階段完成特效全部由你畫**, RD 只傳 state; 提示要貼近它在講的東西(角色、幽靈、機關), 不擋住玩家正在看的路線。上一版有 `drawGuidePage` 就刪掉
- **說明頁分工**(探索 / 深掘): 你只畫**示意圖**, 而且只畫在 `(x, y, w, h)` 這個框內; 頁標題、說明文字、頁碼、翻頁提示、按鍵說明一律由 RD 畫, 你不畫。示意圖裡只允許物件旁的短標籤(例「你」「終點旗」)。兩邊都畫文字會重疊(GhostEchoV2 探索與深掘各輪都出過)
- 開工前讀經驗文件, style.md 要有「理念落實」一節; 收工前依它的規則判斷要不要寫經驗提案到收件匣(見共同守則)
- 收工前用 Node 把每個匯出函式(探索 / 深掘含每一頁說明頁; 打磨含每個教學階段與完成特效的各進度)都用假 ctx 呼叫一次, 確認不拋錯

## 回報
產了哪些函式、畫布尺寸、寫了哪幾條經驗提案與理念異動(沒有就說無)。
