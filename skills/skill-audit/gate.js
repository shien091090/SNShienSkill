#!/usr/bin/env node
// skill-audit 的 commit 關卡。兩種用法:
//   PreToolUse hook(stdin 收 hook JSON): git commit 的 staged 檔案落在某個 skill 目錄內,
//     且該目錄的 staged 內容還沒 audit 過 → deny, 要 Claude 先跑 skill-audit
//   node gate.js --stamp <skill 目錄>: audit 完、重新 git add 後呼叫, 記下目前 staged 內容的指紋
// 指紋存在 ~/.claude/skill-audit-stamps.json(被 ~/.claude/.gitignore 的 * 排除, 只留本機)
const { execFileSync } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const os = require('os');

const STAMP_FILE = path.join(os.homedir(), '.claude', 'skill-audit-stamps.json');

function git(cwd, args) {
  return execFileSync('git', ['-C', cwd, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
}

function loadStamps() {
  try { return JSON.parse(fs.readFileSync(STAMP_FILE, 'utf8')); } catch { return {}; }
}

function keyOf(dir) {
  return path.resolve(dir).replace(/\\/g, '/').toLowerCase();
}

// 目錄內工作區內容的指紋(追蹤中 + 未追蹤且未被忽略的檔案)。
// 用工作區而非 index: `git add ... && git commit` 同一行時, hook 執行當下還沒 add
function fingerprint(skillDir) {
  const root = git(skillDir, ['rev-parse', '--show-toplevel']).trim();
  const rel = path.relative(root, skillDir).replace(/\\/g, '/') || '.';
  const files = git(root, ['ls-files', '-co', '--exclude-standard', '--', rel]).split('\n').filter(Boolean).sort();
  const h = crypto.createHash('sha1');
  for (const f of files) {
    h.update(f + '\0');
    try { h.update(fs.readFileSync(path.join(root, f))); } catch { /* 已刪除的檔案只計路徑 */ }
  }
  return h.digest('hex');
}

function hasSkillMd(dir) {
  try { return fs.readdirSync(dir).some(f => f.toLowerCase() === 'skill.md'); } catch { return false; }
}

// 從檔案往上找到第一個含 SKILL.md 的目錄, 不超出 repo 根
function findSkillDir(root, relFile) {
  let dir = path.dirname(path.join(root, relFile));
  const top = path.resolve(root);
  while (path.resolve(dir).length >= top.length) {
    if (hasSkillMd(dir)) return path.resolve(dir);
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

// 從指令推 commit 發生在哪個目錄: git -C <path>, 或 commit 之前最後一個 cd / Set-Location, 否則用 hook 的 cwd
function repoDirOf(command, commit, cwd) {
  const unq = s => s.replace(/^["']|["']$/g, '');
  let m = commit[0].match(/\bgit\s+-C\s+("[^"]+"|'[^']+'|\S+)/);
  if (m) return path.resolve(cwd, unq(m[1]));
  const cds = [...command.slice(0, commit.index).matchAll(/(?:^|[;&|]\s*|\n\s*)(?:cd|Set-Location)\s+("[^"]+"|'[^']+'|[^\s;&|]+)/gi)];
  if (cds.length) return path.resolve(cwd, unq(cds[cds.length - 1][1]));
  return cwd;
}

function stamp(dir) {
  const stamps = loadStamps();
  stamps[keyOf(dir)] = fingerprint(dir);
  fs.writeFileSync(STAMP_FILE, JSON.stringify(stamps, null, 2));
  console.log(`stamped ${path.resolve(dir)}`);
}

function gate(input) {
  const command = (input.tool_input && input.tool_input.command) || '';
  const commit = command.match(/\bgit\b[^;&|\n]*\bcommit\b/);
  if (!commit) return;
  const repoDir = repoDirOf(command, commit, input.cwd || process.cwd());
  let root, staged;
  try {
    root = git(repoDir, ['rev-parse', '--show-toplevel']).trim();
    staged = git(root, ['diff', '--cached', '--name-only', '--diff-filter=ACMR']).split('\n').filter(Boolean);
    // 同一行指令裡會先 add(或 commit -a)時, 工作區的變更也算這次 commit 的一部分
    if (/\bgit\b[^;&|\n]*\badd\b/.test(command) || /\bcommit\b[^;&|\n]*\s(--all|-[a-zA-Z]*a[a-zA-Z]*)\b/.test(command)) {
      staged = staged.concat(
        git(root, ['diff', '--name-only', '--diff-filter=ACMR']).split('\n'),
        git(root, ['ls-files', '--others', '--exclude-standard']).split('\n')
      ).filter(Boolean);
    }
  } catch { return; }

  const dirs = new Set();
  for (const f of staged) {
    const d = findSkillDir(root, f);
    if (d) dirs.add(d);
  }
  const stamps = loadStamps();
  const pending = [...dirs].filter(d => stamps[keyOf(d)] !== fingerprint(d));
  if (!pending.length) return;

  const selfPath = __filename.replace(/\\/g, '/');
  const list = pending.map(d => `- ${d.replace(/\\/g, '/')}`).join('\n');
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason:
        `這次 commit 含有尚未 audit 的 skill 變更:\n${list}\n` +
        `先用 skill-audit skill 逐一檢查並修正, 修正的檔案重新 git add, ` +
        `再對每個目錄執行 node "${selfPath}" --stamp "<skill 目錄>", 最後重新 commit。`
    }
  }));
}

if (process.argv[2] === '--stamp') {
  if (!process.argv[3]) { console.error('usage: node gate.js --stamp <skill dir>'); process.exit(1); }
  stamp(process.argv[3]);
} else {
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', c => raw += c);
  process.stdin.on('end', () => {
    let input;
    try { input = JSON.parse(raw); } catch { process.exit(0); }
    try { gate(input); } catch { /* 關卡本身出錯時放行, 不卡住 commit */ }
    process.exit(0);
  });
}
