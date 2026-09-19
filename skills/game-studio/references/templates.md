# game-studio 文件模板

製作人建檔時照抄章節; agent 寫檔時製作人在 prompt 裡貼對應段落。章節名不改, 後面的狀態參考檔靠章節名指路。

## STATE.md

```
state: concept
round:
  spec-draft: 0
  playtest: 0
log:
- YYYY-MM-DD 建立, 概念寫入 concept.md
```

- `state`: concept | spec-draft | spec-review | build | playtest | done
- `round.spec-draft`: 進入 spec-draft 時 +1; 值即現行 spec 版號
- `round.playtest`: 進入 playtest 時 +1; 值即現行 feedback 輪號
- log 一行一事件, 日期開頭, 新的加最下面; 退回要寫理由

## concept.md

```
# 概念發想

(使用者原文, 一字不改)

---
收錄日期: YYYY-MM-DD
```

## decisions.md

```
# 定案結果

## 遊戲名(暫定)
## 一句話概念
## 核心循環
玩家做什麼 → 得到什麼 → 為什麼想再做一次, 三到五句
## Demo 要驗證的問題
一句話, 只有一個問題
## 確定要有的
-
## 明確不做的
-
## 數值方向
目標單局時長、難度曲線走向、關鍵參數區間(數值同事的結論)
## 留給規格階段決定的
-
## 修訂紀錄
- v1 YYYY-MM-DD concept 定案
- v2 YYYY-MM-DD 觸發: spec-review 退回 / playtest 第 N 輪玩法回饋; 改了: ...; 原因: ...
```

## spec.md

```
# Demo 規格 v{N}

## 概述
對應 decisions.md 的一句話概念與驗證問題
## 核心循環
## 規則
條列, 每條一個可判定的行為
## 操作
輸入 → 行為, 鍵盤與滑鼠都列
## 勝負與結束條件
## 數值參數表
| 參數 | 值 | 說明 |
## 物件清單
| 物件 | 狀態 | 說明 |
只寫是什麼、有哪些狀態; 不寫外觀
## Demo 範圍邊界
- 不做:
## 待定
- (項目: 原因), 沒有就寫無
```

## feedback/round-{N}.md

```
# 試玩回饋 第 {N} 輪

日期: YYYY-MM-DD
版本: spec v{M}

## bug
- [ ] 描述; 重現步驟
## 玩法
- 描述
## 美術
- 描述

## 製作人處理
- bug: 已交 RD 修復 / 無
- 玩法: 併入 decisions.md v{K} / 無
- 美術: 留待下次 build 交美術 / 無
```

bug 條目修完打勾。玩法與美術段在使用者確認「本輪講完」前持續追加。
