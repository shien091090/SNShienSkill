---
name: feedback-prefer-open-text-over-askuserquestion
description: 討論 skill/workflow 或程式架構設計細節時，使用者多次拒絕 AskUserQuestion 多選工具，偏好直接文字問答
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c9224df2-9edd-43de-87df-d5f63da7dcf6
  modified: 2026-07-24T05:32:12.569Z
---

在 808 Lobby 專案（[[lobby]] 相關工作）中討論任何有一定複雜度的設計判斷時——不只是 Skill workflow 機制（拆解模塊、迭代模塊等），也包含**程式架構/實作方案的設計討論**（例如 2026-07-24 討論 IconViewPresenter 該不該包一層 `DRT_IconViewOpener`、或改用既有 BindView 模式），使用者多次明確拒絕 AskUserQuestion 的多選題形式，選擇直接用自己的文字說明想法/反問。

**Why:** 這類問題通常牽涉複雜的、環環相扣的判斷（架構取捨、流程設計），使用者想要的是開放式對話讓他能補充脈絡、糾正誤解、或用一個反問把我導向更好的既有解法，而不是被限制在預先猜測的選項裡。多選題容易漏掉他真正想表達的細節。

**How to apply:** 當正在跟這位使用者討論 skill/流程設計或程式架構設計的機制性細節（不是單純的路徑/命名這種簡單二選一）時，優先用純文字直接提問或給方案讓他評論，不要用 AskUserQuestion 工具。如果使用者主動用 AskUserQuestion 回答過類似問題（例如簡單的命名、路徑選擇），那種情境下工具還是可以用；但只要被拒絕一次，就該記住這次對話裡這類問題都改用文字問。
