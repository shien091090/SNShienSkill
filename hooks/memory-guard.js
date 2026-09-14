#!/usr/bin/env node
// PreToolUse hook: auto-memory 只允許 project_*.md 與 MEMORY.md
// 其他類型(feedback/reference/user)該進 rule 或 skill, 見 ~/.claude/rules/memory-policy.md
let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', c => raw += c);
process.stdin.on('end', () => {
  let input;
  try { input = JSON.parse(raw); } catch { process.exit(0); }
  const p = (input.tool_input && input.tool_input.file_path) || '';
  const norm = p.replace(/\\/g, '/');
  const m = norm.match(/\/\.claude\/projects\/[^/]+\/memory\/([^/]+)$/i);
  if (!m) process.exit(0);
  const name = m[1];
  if (name === 'MEMORY.md' || /^project_/.test(name)) process.exit(0);
  const out = {
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason:
        `memory 只允許 project_*.md(進行中、跨 session 要接的工作)。「${name}」不是。` +
        ` 使用者糾正/偏好 → ~/.claude/rules/ 或該 SKILL.md; 路徑/URL → 專案 CLAUDE.md 或 spec。` +
        ` 詳見 ~/.claude/rules/memory-policy.md`
    }
  };
  process.stdout.write(JSON.stringify(out));
  process.exit(0);
});
