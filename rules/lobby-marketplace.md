---
paths:
  - "D:/Git/lobby-agent-client/**"
  - "C:/Users/lithoshu/.claude/plugins-src/**"
  - "C:/Users/lithoshu/.claude/skills/dashboard/**"
---

# lobby-agent-client 市集上架規則

現有的 skill-gate、dashboard 維持各自獨立的 plugin, 不合併、不搬動。

**從第 3 個工具開始**: 不再新增獨立的 plugin。改成建立一個 `lobby-tools` plugin, 第 3 個工具和之後所有的新工具都放進它裡面。每次加工具都要升 `lobby-tools` 的版號再推。

**Why:** 獨立 plugin 每多一個, 同事就要多打一次 `/plugin install`。全部放在同一個 plugin 裡, 同事只要裝一次、打開市集自動更新, 之後新工具會在開新 session 時自動出現, 也不綁專案。代價是同事只能全裝或全不裝。
