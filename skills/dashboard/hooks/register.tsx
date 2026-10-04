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
// 自動命名: 記下第一則訊息, 第一輪回應完且還沒命名時請 haiku 取一個名字(只試一次)
const firstPrompt = atom({ plugin: 'dashboard', key: 'firstPrompt' } as const, '')
const autoTried = atom({ plugin: 'dashboard', key: 'autoTried' } as const, false)
const isAutoTitle = atom({ plugin: 'dashboard', key: 'isAutoTitle' } as const, false)

const AUTO_TITLE_SYSTEM =
  '你負責替 Claude Code 的一段對話取簡短標題。只輸出標題本身: 繁體中文, 6 到 16 個字, 不加引號、不加句尾標點、不要解釋。'
const AUTO_TITLE_MAX = 24

export function autoTitlePrompt(prompt: string, answer: string): string {
  return `使用者的第一則訊息:\n${prompt.slice(0, 1000)}\n\n助理回覆的開頭:\n${answer.slice(0, 600)}`
}

// 模型回覆整理成一行標題: 取第一行、去掉引號與句尾標點、限制長度
export function cleanTitle(text: string): string {
  const line = text.split('\n').map(l => l.trim()).find(l => l.length > 0) ?? ''
  const bare = line.replace(/^["'「『《]+|["'」』》]+$/g, '').replace(/[。．.!！?？]+$/, '').trim()
  return bare.length > AUTO_TITLE_MAX ? bare.slice(0, AUTO_TITLE_MAX) : bare
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

async function refreshModel($: EngineInterface) {
  const name = prettyModel(await $.session.model())
  await update($, model, () => name)
}

// 第一輪主對話回應完, 還沒有名稱就自動取一個; 回傳 { done } 包住取名的 promise, 呼叫端不必等它完成
async function maybeAutoTitle($: EngineInterface, answer: string): Promise<{ done: Promise<void> }> {
  const idle = { done: Promise.resolve() }
  if ((await read($, title)) || (await read($, autoTried))) return idle
  const prompt = await read($, firstPrompt)
  if (!prompt) return idle

  await update($, autoTried, () => true)
  const done = $.model
    .complete({
      model: 'haiku',
      system: AUTO_TITLE_SYSTEM,
      prompt: autoTitlePrompt(prompt, answer),
      maxTokens: 64,
      effort: 'low',
      timeoutMs: 20_000,
    })
    .then(async r => {
      const name = r.isAnswered ? cleanTitle(r.text) : ''
      // 等待期間使用者已手動命名就不覆蓋
      if (!name || (await read($, title))) return
      await update($, title, () => name)
      await update($, isAutoTitle, () => true)
      await update($, pendingTitle, () => name)
    })
    .catch(() => {})
  return { done }
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

    return result
  })

  // 用 /model 換模型後, 下一次送出或量測時更新名字
  on('prompt.submit', async ($, e, next) => {
    await refreshModel($)
    return next(e)
  })

  on('classic.SessionStart', async ($, e, next) => {
    const result = await next(e)
    if (e.session_title) await update($, title, () => e.session_title!)
    return result
  })

  // 送出訊息時: 有待寫入的新名稱就寫進 session; 否則同步 /rename 等方式改的名稱
  on('classic.UserPromptSubmit', async ($, e, next) => {
    const result = await next(e)
    if (!(await read($, firstPrompt))) await update($, firstPrompt, () => e.prompt)
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

    // 第一輪會先自動取名, 取好再發通知, 讓通知標題就是新名稱
    const naming = e.reason === 'answer' ? await maybeAutoTitle($, e.answer) : { done: Promise.resolve() }
    void naming.done.then(async () => sendToast($, await read($, title), e.reason, e.answer)).catch(() => {})
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
              </Box>
            )}
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
