#!/usr/bin/env node
const { execSync } = require('child_process');
const path = require('path');

let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
    const data = JSON.parse(input);

    // ── 基本資訊 ──────────────────────────────────────
    const model   = data.model?.display_name || data.model?.id || 'Claude';
    const dir     = data.workspace?.current_dir || '';
    const version = data.version || '';
    const agent   = data.agent?.name || '';
    const vimMode = data.vim?.mode || '';

    // ── Context Window ────────────────────────────────
    const usedTokens = data.context_window?.used_tokens || 0;
    const maxTokens  = data.context_window?.max_tokens  || 0;
    const pct        = maxTokens > 0
        ? Math.floor((usedTokens / maxTokens) * 100)
        : Math.floor(data.context_window?.used_percentage || 0);
    const ctxSize    = data.context_window?.context_window_size || maxTokens;
    const ctxLabel   = ctxSize >= 1_000_000 ? '1M' : ctxSize > 0 ? '200K' : '';

    // ── Token 費用 ────────────────────────────────────
    const cost        = data.cost?.total_cost_usd      || 0;
    const durationMs  = data.cost?.total_duration_ms   || 0;
    const apiDurMs    = data.cost?.total_api_duration_ms || 0;
    const linesAdd    = data.cost?.total_lines_added    ?? null;
    const linesDel    = data.cost?.total_lines_removed  ?? null;

    // ── Token 詳情 ────────────────────────────────────
    const totalIn     = data.context_window?.total_input_tokens  || 0;
    const totalOut    = data.context_window?.total_output_tokens || 0;
    const curInput    = data.context_window?.current_usage?.input_tokens               || 0;
    const cacheRead   = data.context_window?.current_usage?.cache_read_input_tokens    || 0;
    const cacheCreate = data.context_window?.current_usage?.cache_creation_input_tokens || 0;

    // ── Rate Limits ───────────────────────────────────
    const rate5h      = data.rate_limits?.five_hour?.used_percentage ?? null;
    const rate7d      = data.rate_limits?.seven_day?.used_percentage ?? null;
    const reset5h     = data.rate_limits?.five_hour?.resets_at       ?? null;
    const reset7d     = data.rate_limits?.seven_day?.resets_at       ?? null;

    // ── 顏色 ──────────────────────────────────────────
    const CYAN    = '\x1b[36m';
    const GREEN   = '\x1b[32m';
    const YELLOW  = '\x1b[33m';
    const RED     = '\x1b[31m';
    const MAGENTA = '\x1b[35m';
    const BLUE    = '\x1b[34m';
    const WHITE   = '\x1b[37m';
    const BOLD    = '\x1b[1m';
    const DIM     = '\x1b[2m';
    const RESET   = '\x1b[0m';
    const SEP     = `${DIM} | ${RESET}`;

    // ── Helper: 顏色依百分比 ──────────────────────────
    const colorPct = pct => pct >= 80 ? RED : pct >= 50 ? YELLOW : GREEN;

    // ── Helper: 格式化時間 ────────────────────────────
    const fmtDur = ms => {
        const s = Math.floor(ms / 1000);
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        const sec = s % 60;
        if (h > 0) return `${h}h ${String(m).padStart(2,'0')}m`;
        if (m > 0) return `${m}m ${String(sec).padStart(2,'0')}s`;
        return `${sec}s`;
    };

    // ── Helper: 倒數計時（epoch → Xh Ym）────────────
    const fmtCountdown = (epoch, hoursOnly = false) => {
        const diff = Math.floor(epoch - Date.now() / 1000);
        if (diff <= 0) return 'now';
        const h = Math.floor(diff / 3600);
        const m = Math.floor((diff % 3600) / 60);
        if (hoursOnly) return `${h}h ${m}m`;
        return `${h}h ${m}m`;
    };

    // ── Helper: 格式化 token 數 ───────────────────────
    const fmtK = n => {
        if (!n) return '0';
        if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
        if (n >= 1_000)     return (n / 1_000).toFixed(1) + 'K';
        return String(n);
    };

    // ── Context 進度條（原版樣式）────────────────────
    const barColor = pct >= 90 ? RED : pct >= 70 ? YELLOW : GREEN;
    const filled   = Math.floor(pct / 10);
    const bar      = `${barColor}${'▉'.repeat(filled)}${DIM}${'▁'.repeat(10 - filled)}${RESET}`;

    // ── Git info ──────────────────────────────────────
    let branch = '';
    let repoLink = path.basename(dir);
    let gitStats = '';

    const inGit = (() => {
        try { execSync('git rev-parse --git-dir', { stdio: 'ignore' }); return true; }
        catch { return false; }
    })();

    if (inGit) {
        try {
            branch = execSync('git branch --show-current', { encoding: 'utf8', stdio: ['pipe','pipe','ignore'] }).trim();
        } catch {}

        // Repo 超連結
        try {
            const remote = execSync('git remote get-url origin', { encoding: 'utf8', stdio: ['pipe','pipe','ignore'] })
                .trim()
                .replace(/^git@github\.com:/, 'https://github.com/')
                .replace(/\.git$/, '');
            const repoName = path.basename(remote);
            repoLink = `\x1b]8;;${remote}\x07${repoName}\x1b]8;;\x07`;
        } catch {
            repoLink = path.basename(dir);
        }

        // Git file stats
        try {
            const modified = parseInt(execSync('git diff --name-only 2>/dev/null | wc -l', { encoding: 'utf8', shell: true }).trim()) || 0;
            const added    = parseInt(execSync('git ls-files --others --exclude-standard 2>/dev/null | wc -l', { encoding: 'utf8', shell: true }).trim()) || 0;
            const deleted  = parseInt(execSync('git diff --diff-filter=D --name-only 2>/dev/null | wc -l', { encoding: 'utf8', shell: true }).trim()) || 0;
            const parts = [];
            if (modified > 0) parts.push(`${YELLOW}${modified}M${RESET}`);
            if (added    > 0) parts.push(`${GREEN}${added}A${RESET}`);
            if (deleted  > 0) parts.push(`${RED}${deleted}D${RESET}`);
            if (parts.length) gitStats = parts.join(' ');
        } catch {}
    }

    // ── Cache hit rate ────────────────────────────────
    let cacheHit = '';
    const cacheTotal = curInput + cacheRead + cacheCreate;
    if (cacheTotal > 0 && cacheRead >= 0) {
        const cachePct = Math.floor(cacheRead * 100 / cacheTotal);
        const cc = colorPct(100 - cachePct);
        cacheHit = `${DIM}cache${RESET} ${cc}${cachePct}%${RESET}`;
    }

    // ══════════════════════════════════════════════════
    // LINE 1: Model + ctx size + version + repo + branch + lines + git stats + agent + vim
    // ══════════════════════════════════════════════════
    let L1 = `${CYAN}${BOLD}${model}${RESET}`;
    if (ctxLabel) L1 += ` ${DIM}${ctxLabel}${RESET}`;
    if (version)  L1 += ` ${DIM}v${version}${RESET}`;
    L1 += `${SEP}📁 ${WHITE}${repoLink}${RESET}`;
    if (branch)   L1 += ` 🌿 ${DIM}${branch}${RESET}`;

    // Lines added / removed
    const linesParts = [];
    if (linesAdd !== null && linesAdd !== 0) linesParts.push(`${GREEN}+${linesAdd}${RESET}`);
    if (linesDel !== null && linesDel !== 0) linesParts.push(`${RED}-${linesDel}${RESET}`);
    if (linesParts.length) L1 += `${SEP}${linesParts.join(' ')} ${DIM}lines${RESET}`;

    if (gitStats) L1 += `${SEP}${gitStats}`;
    if (agent)    L1 += `${SEP}${MAGENTA}${agent}${RESET}`;
    if (vimMode)  L1 += `${SEP}${vimMode === 'NORMAL' ? `${BLUE}${BOLD}NOR${RESET}` : `${GREEN}${BOLD}INS${RESET}`}`;

    // ══════════════════════════════════════════════════
    // LINE 2: Context bar + cost + duration + rate limits
    // ══════════════════════════════════════════════════
    const costFmt = `$${cost.toFixed(2)}`;
    let L2 = `[${bar}] ${barColor}${pct}%${RESET}${SEP}${YELLOW}${costFmt}${RESET}${SEP}${DIM}⏱ ${fmtDur(durationMs)}${RESET}`;

    // reset time group — only show if at least one rate limit exists
    if (rate5h !== null || rate7d !== null) {
        const rateParts = [];
        if (rate5h !== null) {
            const r5 = Math.round(rate5h);
            const r5c = colorPct(r5);
            let part = `${DIM}5h${RESET} ${r5c}${r5}%${RESET}`;
            if (reset5h) part += ` ${DIM}(${fmtCountdown(reset5h)})${RESET}`;
            rateParts.push(part);
        }
        if (rate7d !== null) {
            const r7 = Math.round(rate7d);
            const r7c = colorPct(r7);
            let part = `${DIM}7d${RESET} ${r7c}${r7}%${RESET}`;
            if (reset7d) part += ` ${DIM}(${fmtCountdown(reset7d, true)})${RESET}`;
            rateParts.push(part);
        }
        L2 += `${SEP}${DIM}reset time${RESET}( ${rateParts.join(` ${DIM}|${RESET} `)} )`;
    }

    // ══════════════════════════════════════════════════
    // LINE 3: Cache | api wait | session token
    // ══════════════════════════════════════════════════
    const parts3 = [];

    if (cacheHit) parts3.push(cacheHit);

    // API wait
    const apiDurStr = fmtDur(apiDurMs);
    if (durationMs > 0 && apiDurMs > 0) {
        const apiPct = Math.round(apiDurMs * 100 / durationMs);
        parts3.push(`${DIM}api wait${RESET} ${CYAN}${apiDurStr}${RESET} ${DIM}(${apiPct}%)${RESET}`);
    } else {
        parts3.push(`${DIM}api wait${RESET} ${CYAN}${apiDurStr}${RESET}`);
    }

    // Session token
    parts3.push(
        `${DIM}session token${RESET}(${DIM}in:${RESET} ${CYAN}${fmtK(totalIn)}${RESET} ${DIM}out:${RESET} ${MAGENTA}${fmtK(totalOut)}${RESET})`
    );

    const L3 = parts3.join(SEP);

    // ══════════════════════════════════════════════════
    // LINE 4: usage( cur  read  write )
    // ══════════════════════════════════════════════════
    const L4 =
        `${DIM}usage${RESET}(` +
        `${DIM}cur${RESET} ${CYAN}${fmtK(curInput)}${RESET}  ` +
        `${DIM}read${RESET} ${CYAN}${fmtK(cacheRead)}${RESET}  ` +
        `${DIM}write${RESET} ${CYAN}${fmtK(cacheCreate)}${RESET}` +
        `)`;

    // ── 輸出 ──────────────────────────────────────────
    console.log();
    console.log(L1);
    console.log(L2);
    console.log(L3);
    console.log(L4);
    console.log();
});
