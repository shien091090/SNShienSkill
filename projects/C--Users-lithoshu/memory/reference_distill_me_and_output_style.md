---
name: reference-distill-me-and-output-style
description: "claude-distill-me 安裝位置與 Lithoshu Voice output style 檔案位置, 重跑蒸餾或調整風格時用"
metadata: 
  node_type: memory
  type: reference
  originSessionId: febcf7f1-ae9f-46f7-9410-d43ff0e44262
  modified: 2026-08-13T04:07:41.484Z
---

2026-08-13 安裝了 [claude-distill-me](https://github.com/LewenW/claude-distill-me) 並跑完蒸餾流程:

- repo 位置: `C:\Users\lithoshu\claude-distill-me`, venv 在 `.venv`(Python 3.12, mcp 需 <2, 已 pin), 已用 `claude mcp add distill-me -s user` 註冊(工具: scan_user_data / save_extracted_patterns / generate_personal_skill)
- 蒸餾出的 patterns: `C:\Users\lithoshu\.claude\distill-me\patterns\`(judgment/style/priorities 三檔, 重跑會自動備份)
- enhanced-self SKILL.md: `C:\Users\lithoshu\claude-distill-me\skills\enhanced-self\SKILL.md`(未注入 ~/.claude/CLAUDE.md, 使用者目標是 output style 不是全域注入)
- **output style 檔案: `C:\Users\lithoshu\.claude\output-styles\lithoshu-voice.md`**(name: Lithoshu Voice), 啟用方式: `/config` → Output style; `/output-style` 指令已於 v2.1.91 移除

重跑蒸餾: 用 repo venv 的 python 直接呼叫 distill_me 的 scanner/generator 函式即可(MCP 工具也可, 但要 session 啟動時已註冊)。
