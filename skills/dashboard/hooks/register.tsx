import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, SessionContextUsage, SessionRateLimit } from 'claude-code'

import type { Gauge, Tokens } from '../types'
import { TAG_CHARS, TOAST_SCRIPT, toastText } from './notify'

const gauges = atom({ plugin: 'dashboard', key: 'gauges' } as const, [] as Gauge[])
const model = atom({ plugin: 'dashboard', key: 'model' } as const, '')
const tokens = atom({ plugin: 'dashboard', key: 'tokens' } as const, { input: 0, output: 0 } as Tokens)
const cost = atom({ plugin: 'dashboard', key: 'cost' } as const, null as number | null)
// session 名稱: 改名後先顯示在儀表板, 下次送出訊息時才真正寫進 session
const title = atom({ plugin: 'dashboard', key: 'title' } as const, '')
const pendingTitle = atom({ plugin: 'dashboard', key: 'pendingTitle' } as const, null as string | null)
const isEditing = atom({ plugin: 'dashboard', key: 'isEditing' } as const, false)
// 自動命名: Claude Code 本身會替 session 取 AI 標題並寫進對話紀錄檔, 還沒有名稱時讀那個來用
const transcriptPath = atom({ plugin: 'dashboard', key: 'transcriptPath' } as const, '')
const isAutoTitle = atom({ plugin: 'dashboard', key: 'isAutoTitle' } as const, false)
// 快捷按鈕列: 按「⋯ 快捷」展開, 選了其中一項就收起來
const isMenuOpen = atom({ plugin: 'dashboard', key: 'isMenuOpen' } as const, false)
// 這個 session 跑過 /remote-control 就當作已啟動; 外掛讀不到真正的連線狀態, 再跑一次只會開狀態面板(斷開也在那裡)
const isRemoteOn = atom({ plugin: 'dashboard', key: 'isRemoteOn' } as const, false)
// 快捷按鈕列的項目: 送出一段固定的 prompt, 或執行一個斜線指令
export const SAVE_STATE_PROMPT =
  '請記憶目前工作狀態,我要重開一個新的session再繼續,並給我重開session後要講什麼關鍵字才能繼續'
export const QUICK_ACTIONS = [
  { key: 'quick-save-state', label: '記憶工作狀態', prompt: SAVE_STATE_PROMPT },
  { key: 'quick-remote-control', label: '啟動RemoteControl', onLabel: 'RemoteControl 狀態', command: 'remote-control' },
] as const

// 第一輪結束時 AI 標題可能還沒寫好, 晚一點再讀一次
const TITLE_RETRY_MS = 8_000

// 從對話紀錄找最新的名稱: 手動改的(custom-title)優先於 AI 取的(ai-title)
export function latestTitle(jsonl: string): { title: string; isAuto: boolean } | null {
  const lines = jsonl.split('\n')
  let ai: string | null = null
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i]!
    if (!line.includes('-title"')) continue
    try {
      const row = JSON.parse(line) as { type?: string; customTitle?: string; aiTitle?: string }
      if (row.type === 'custom-title' && row.customTitle) return { title: row.customTitle, isAuto: false }
      if (row.type === 'ai-title' && row.aiTitle && ai === null) ai = row.aiTitle
    } catch {
      // 不是完整的一列就略過
    }
  }
  return ai ? { title: ai, isAuto: true } : null
}

const LABELS: Record<string, string> = {
  five_hour: '5h',
  seven_day: '7d',
  spend_limit: '$$',
}
const ORDER = ['ctx', '5h', '7d']

// 區塊之間的分隔線
export const SEP = ' │ '
const MIN_BAR = 4
const MAX_BAR = 12
const EMPTY_BG = '#3a3a3a'

// 模型名稱: 平常是底色, 工作中有一道亮光從左掃到右, 前面加轉圈符號
const MODEL_BASE = '#d97757'
const MODEL_SHINE = '#ffe3d3'
const SPINNER = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
const IDLE_MARK = '⠿'
const FRAME_MS = 100
const MODEL_POLL_MS = 1_000

// 模型識別字轉成好讀的名字: claude-opus-5-5[1m] → Opus 5.5
export function prettyModel(id: string): string {
  const m = id.match(/claude-([a-z]+)-(\d+)(?:-(\d{1,2}))?(?:-\d{8})?/i)
  if (!m) return id.replace(/^claude\s+/i, '').trim()
  const name = m[1]!.charAt(0).toUpperCase() + m[1]!.slice(1)
  return m[3] ? `${name} ${m[2]}.${m[3]}` : `${name} ${m[2]}`
}

function mix(a: string, b: string, t: number): string {
  const pa = [1, 3, 5].map(i => parseInt(a.slice(i, i + 2), 16))
  const pb = [1, 3, 5].map(i => parseInt(b.slice(i, i + 2), 16))
  return '#' + pa.map((v, i) => Math.round(v + (pb[i]! - v) * t).toString(16).padStart(2, '0')).join('')
}

// 每個字的顏色: 亮光位置隨時間移動, 離亮光越近越亮
export function shimmer(name: string, now: number): string[] {
  const span = name.length + 6
  const pos = ((now / 80) % span) - 3
  return Array.from(name, (_, i) => mix(MODEL_BASE, MODEL_SHINE, Math.max(0, 1 - Math.abs(i - pos) / 2.5)))
}

export function spinnerAt(now: number): string {
  return SPINNER[Math.floor(now / FRAME_MS) % SPINNER.length]!
}

// token 數縮寫: 950 / 12.3k / 1.2M
export function fmtTokens(n: number): string {
  const short = (v: number, unit: string) => `${v.toFixed(1).replace(/\.0$/, '')}${unit}`
  if (n >= 1_000_000) return short(n / 1_000_000, 'M')
  if (n >= 1_000) return short(n / 1_000, 'k')
  return String(n)
}

// 終端機顯示寬度: 中日韓全形字佔 2 格
export function strWidth(text: string): number {
  let w = 0
  for (const ch of text) {
    const c = ch.codePointAt(0)!
    const isWide =
      (c >= 0x1100 && c <= 0x115f) ||
      (c >= 0x2e80 && c <= 0xa4cf) ||
      (c >= 0xac00 && c <= 0xd7a3) ||
      (c >= 0xf900 && c <= 0xfaff) ||
      (c >= 0xfe30 && c <= 0xfe4f) ||
      (c >= 0xff00 && c <= 0xff60) ||
      (c >= 0xffe0 && c <= 0xffe6)
    w += isWide ? 2 : 1
  }
  return w
}

// 第二行血條右邊的資訊: 本 session 的 token 與預估金額
export function infoText(t: Tokens, usd: number | null): string {
  const parts = [`Token消耗 in ${fmtTokens(t.input)}  out ${fmtTokens(t.output)}`]
  if (usd !== null) parts.push(`~$${usd.toFixed(2)}`)
  return parts.join(SEP)
}

export function toGauges(rateLimits: SessionRateLimit[], context: SessionContextUsage): Gauge[] {
  const list: Gauge[] = rateLimits.map(r => ({
    label: LABELS[r.kind] ?? r.kind,
    used: r.percentUsed,
    resetsAt: r.resetsAt,
  }))
  if (context.percent !== undefined) {
    list.push({ label: 'ctx', used: context.percent })
  }
  const rank = (l: string) => (ORDER.includes(l) ? ORDER.indexOf(l) : ORDER.length)
  return list.sort((a, b) => rank(a.label) - rank(b.label))
}

// 剩餘血量: 100 - 已用, 夾在 0~100
export function hp(used: number): number {
  return Math.max(0, Math.min(100, 100 - used))
}

export function hpColor(left: number): string {
  if (left > 50) return 'green'
  if (left > 20) return 'yellow'
  return 'red'
}

// 重置時間: 5h 只顯示時分, 其他顯示月/日
export function resetText(g: Gauge): string {
  if (!g.resetsAt) return ''
  const d = new Date(g.resetsAt)
  if (g.label === '5h') {
    return ` ↻ ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }
  return ` ↻ ${d.getMonth() + 1}/${d.getDate()}`
}

// 半格高細條: 下半格方塊, 上下兩行血條之間自然留出半格空隙
const THIN = '▄'

// 血條後的%數, 固定 5 格寬( 100%)
export function pctText(left: number): string {
  return ' ' + String(Math.round(left)).padStart(3) + '%'
}

// 依可用寬度決定血條長度: 第二行 ctx + 資訊, 第三行 5h/7d; 所有血條等長, 太窄時先拿掉重置時間
export function layout(
  list: Gauge[],
  cols: number,
  info: string,
): { bar: number; showReset: boolean; pad: number } {
  const limits = list.filter(g => g.label !== 'ctx')
  const hasCtx = list.some(g => g.label === 'ctx')
  // ctx 後補空白, 讓第二行的分隔線對齊第三行第一個分隔線
  const padFor = (showReset: boolean) => (showReset && limits[0] ? resetText(limits[0]).length : 0)
  const row2 = (showReset: boolean) =>
    hasCtx ? cols - 4 - 5 - padFor(showReset) - (info ? SEP.length + strWidth(info) : 0) : MAX_BAR
  const row3 = (showReset: boolean) => {
    if (limits.length === 0) return MAX_BAR
    const fixed =
      limits.reduce((sum, g) => sum + 4 + 5 + (showReset ? resetText(g).length : 0), 0) +
      SEP.length * (limits.length - 1)
    return Math.floor((cols - fixed) / limits.length)
  }
  const clampBar = (v: number) => Math.max(MIN_BAR, Math.min(MAX_BAR, v))

  if (Math.min(row2(true), row3(true)) >= MIN_BAR + 2) {
    return { bar: clampBar(Math.min(row2(true), row3(true))), showReset: true, pad: padFor(true) }
  }
  return { bar: clampBar(Math.min(row2(false), row3(false))), showReset: false, pad: 0 }
}

// 名稱沒變就不寫, 免得每次輪詢都觸發重畫
async function runQuickAction($: EngineInterface, action: (typeof QUICK_ACTIONS)[number]) {
  await update($, isMenuOpen, () => false)
  try {
    if ('prompt' in action) await $.prompt.submit({ text: action.prompt, asUser: true })
    else {
      await $.command.run({ command: action.command })
      // 自己呼叫的指令不會經過自己的 command.run 鉤子, 這裡直接記下
      if (action.command === 'remote-control') await update($, isRemoteOn, () => true)
    }
  } catch (err) {
    $.ui.toast(`${action.label} 失敗: ${err instanceof Error ? err.message : String(err)}`)
  }
}

async function refreshModel($: EngineInterface) {
  const name = prettyModel(await $.session.model())
  if (name !== (await read($, model))) await update($, model, () => name)
}

// 還沒有名稱時從對話紀錄讀 Claude Code 取的標題; 有名稱後就不再讀, 免得每輪讀一次大檔案
async function syncTitleFromTranscript($: EngineInterface): Promise<boolean> {
  if (await read($, title)) return true
  const path = await read($, transcriptPath)
  if (!path || !(await $.fs.exists(path))) return false
  const found = latestTitle(await $.fs.read(path))
  if (!found) return false
  await update($, title, () => found.title)
  await update($, isAutoTitle, () => found.isAuto)
  return true
}

// 回應完成的 Windows 通知; 不等它跑完, 避免拖慢回應結束
async function sendToast($: EngineInterface, sessionTitle: string, reason: string, answer: string) {
  const { title: toastTitle, body } = toastText(sessionTitle, await $.session.cwd(), reason, answer)
  const tag = (await $.session.id()).slice(0, TAG_CHARS)
  void $.process
    .run(['powershell', '-NoProfile', '-NonInteractive', '-Command', '-'], {
      stdin: TOAST_SCRIPT,
      env: { CC_TOAST_TITLE: toastTitle, CC_TOAST_BODY: body, CC_TOAST_TAG: tag },
      timeoutMs: 15_000,
    })
    .catch(() => {})
}

export const register: Register = on => {
  // 工作中才需要逐格重畫; 重載時重來無妨
  let isWorking = false

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    const u = await $.session.usage()
    await update($, gauges, () => toGauges(u.rateLimits, u.context))
    await update($, cost, () => u.cost?.usd ?? null)
    await refreshModel($)

    $.clock.every(FRAME_MS, () => {
      if (isWorking) $.ui.invalidate('ui.render')
    })
    // 換模型沒有事件可接(/model 選單選完才生效), 定時檢查一次
    $.clock.every(MODEL_POLL_MS, () => void refreshModel($).catch(() => {}))

    return result
  })

  on('prompt.submit', async ($, e, next) => {
    await refreshModel($)
    return next(e)
  })

  // 直接帶參數的 /model opus 跑完就生效, 立刻更新不等輪詢
  // 手動打 /remote-control 也算啟動, 按鈕文字跟著換
  on('command.run', { command: 'remote-control' }, async ($, e, next) => {
    // 外掛呼叫的指令可能沒帶參數, 補空字串才傳得下去
    const result = await next({ ...e, args: e.args ?? '' })
    await update($, isRemoteOn, () => true)
    return result
  })

  on('command.run', { command: 'model' }, async ($, e, next) => {
    // 外掛呼叫的指令可能沒帶參數, 補空字串才傳得下去
    const result = await next({ ...e, args: e.args ?? '' })
    await refreshModel($)
    return result
  })

  on('classic.SessionStart', async ($, e, next) => {
    const result = await next(e)
    await update($, transcriptPath, () => e.transcript_path)
    if (e.session_title) await update($, title, () => e.session_title!)
    else await syncTitleFromTranscript($)
    return result
  })

  // 送出訊息時: 有待寫入的新名稱就寫進 session; 否則同步 /rename 等方式改的名稱
  on('classic.UserPromptSubmit', async ($, e, next) => {
    const result = await next(e)
    await update($, transcriptPath, () => e.transcript_path)
    const pending = await read($, pendingTitle)
    if (pending) {
      await update($, pendingTitle, () => null)
      return { ...result, sessionTitle: pending }
    }
    if (e.session_title && e.session_title !== (await read($, title))) {
      await update($, title, () => e.session_title!)
      await update($, isAutoTitle, () => false)
    }
    return result
  })

  on('turn.complete', async ($, e, next) => {
    // 主對話與子代理的每一輪都算進本 session 的 token
    const u = e.usage
    if (u) {
      await update($, tokens, t => ({
        input: t.input + u.input_tokens + u.cache_read_input_tokens + u.cache_creation_input_tokens,
        output: t.output + u.output_tokens,
      }))
    }
    const result = await next(e)
    if (e.agentId) return result

    // 先讀名稱再發通知, 讓第一輪的通知標題就是 Claude Code 取的名字
    if (!(await syncTitleFromTranscript($))) {
      $.clock.after(TITLE_RETRY_MS, () => void syncTitleFromTranscript($).catch(() => {}))
    }
    await sendToast($, await read($, title), e.reason, e.answer)
    return result
  })

  on('session.measure', async ($, e, next) => {
    await update($, gauges, () => toGauges(e.rateLimits, e.context))
    await update($, cost, () => e.cost?.usd ?? null)
    await refreshModel($)
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const list = await read($, gauges)
    const name = await read($, model)
    const info = infoText(await read($, tokens), await read($, cost))
    isWorking = e.props.isWorking
    if (e.props.hasSurvey || (list.length === 0 && !name)) {
      return next(e)
    }

    const { Box, Text, Button } = $.ui.resolve(e)
    // 手機版沒有輸入框元件, 只顯示名稱不提供改名
    const Input = e.surface === 'mobile' ? null : $.ui.resolve(e).Input
    const sessionTitle = await read($, title)
    const editing = await read($, isEditing)
    const autoNamed = await read($, isAutoTitle)
    const menuOpen = await read($, isMenuOpen)
    const remoteOn = await read($, isRemoteOn)
    const requestId = e.requestId
    const { bar, showReset, pad } = layout(list, e.props.bodyColumns, info)
    const now = Date.now()
    const ctx = list.find(g => g.label === 'ctx')
    const limits = list.filter(g => g.label !== 'ctx')

    const gauge = (g: Gauge, withSep: boolean) => {
      const left = hp(g.used)
      const color = hpColor(left)
      const filled = Math.round((left / 100) * bar)
      return (
        <Box key={g.label} flexDirection="row">
          {withSep ? <Text dimColor>{SEP}</Text> : null}
          <Text bold>{g.label.padEnd(3)} </Text>
          <Text color={color}>{THIN.repeat(filled)}</Text>
          <Text color={EMPTY_BG}>{THIN.repeat(bar - filled)}</Text>
          <Text color={color}>{pctText(left)}</Text>
          {showReset ? <Text dimColor>{resetText(g)}</Text> : null}
        </Box>
      )
    }

    return (
      <Box flexDirection="column">
        {name ? (
          <Box key="model" flexDirection="row" gap={1}>
            <Box key="model-name" flexDirection="row">
            {isWorking ? (
              <Text color={MODEL_SHINE}>{spinnerAt(now)} </Text>
            ) : (
              <Text color={MODEL_BASE} dimColor>{IDLE_MARK} </Text>
            )}
            {isWorking ? (
              shimmer(name, now).map((c, i) => (
                <Text key={`m${i}`} color={c} bold>
                  {name[i]}
                </Text>
              ))
            ) : (
              <Text color={MODEL_BASE} bold>{name}</Text>
            )}
            </Box>
            <Text dimColor>│</Text>
            {editing && Input ? (
              <Box key="title-edit" flexDirection="row" gap={1}>
                <Input
                  key="title-input"
                  label="名稱 "
                  placeholder="輸入 session 名稱, Enter 確定"
                  value={sessionTitle}
                  submitLabel="確定"
                  autoFocus
                  onSubmit={(value: string) => {
                    const newTitle = value.trim()
                    void (async () => {
                      if (newTitle) {
                        await update($, title, () => newTitle)
                        await update($, isAutoTitle, () => false)
                        await update($, pendingTitle, () => newTitle)
                      }
                      await update($, isEditing, () => false)
                    })()
                  }}
                />
                <Button key="title-cancel" label="取消" onPress={() => update($, isEditing, () => false)} />
              </Box>
            ) : (
              <Box key="title-view" flexDirection="row" gap={1}>
                {sessionTitle ? (
                  <Text bold={!autoNamed} italic={autoNamed}>
                    {sessionTitle}
                  </Text>
                ) : (
                  <Text dimColor>未命名</Text>
                )}
                {Input ? (
                <Button
                  key="title-rename"
                  label="改名"
                  onPress={() => {
                    void (async () => {
                      await update($, isEditing, () => true)
                      await $.ui.focus({ requestId, key: 'title-input' }).catch(() => {})
                    })()
                  }}
                />
                ) : null}
                <Button
                  key="quick-toggle"
                  label={menuOpen ? '⋯ 收起' : '⋯ 快捷'}
                  dimColor={!menuOpen}
                  onPress={() => update($, isMenuOpen, open => !open)}
                />
              </Box>
            )}
          </Box>
        ) : null}
        {menuOpen ? (
          <Box key="quick-row" flexDirection="row" gap={1}>
            {QUICK_ACTIONS.map(action => (
              <Button
                key={action.key}
                label={'onLabel' in action && remoteOn ? action.onLabel : action.label}
                onPress={() => void runQuickAction($, action)}
              />
            ))}
          </Box>
        ) : null}
        <Box key="ctx-row" flexDirection="row">
          {ctx ? gauge(ctx, false) : null}
          {ctx && pad > 0 ? <Text>{' '.repeat(pad)}</Text> : null}
          {ctx ? <Text dimColor>{SEP}</Text> : null}
          <Text>{info}</Text>
        </Box>
        {limits.length > 0 ? (
          <Box key="limit-row" flexDirection="row">
            {limits.map((g, i) => gauge(g, i > 0))}
          </Box>
        ) : null}
      </Box>
    )
  })
}
