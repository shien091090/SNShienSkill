import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, SessionContextUsage, SessionRateLimit } from 'claude-code'

import type { Gauge, Tokens } from '../types'

const gauges = atom({ plugin: 'dashboard', key: 'gauges' } as const, [] as Gauge[])
const model = atom({ plugin: 'dashboard', key: 'model' } as const, '')
const tokens = atom({ plugin: 'dashboard', key: 'tokens' } as const, { input: 0, output: 0 } as Tokens)
const cost = atom({ plugin: 'dashboard', key: 'cost' } as const, null as number | null)

const LABELS: Record<string, string> = {
  five_hour: '5h',
  seven_day: '7d',
  spend_limit: '$$',
}
const ORDER = ['ctx', '5h', '7d']

// 區塊之間的分隔線
export const SEP = ' │ '
const MIN_BAR = 6
const MAX_BAR = 20
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

// 第二行血條右邊的資訊: 本 session 的 token 與預估金額
export function infoText(t: Tokens, usd: number | null): string {
  const parts = [`in ${fmtTokens(t.input)}  out ${fmtTokens(t.output)}`]
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

// 血條拆成連續片段: %數置中疊在血條上, 每段標記是否在已填滿的範圍內
export type Segment = { text: string; isFilled: boolean }

export function segments(left: number, bar: number): Segment[] {
  const filled = Math.round((left / 100) * bar)
  const label = `${Math.round(left)}%`
  const start = Math.floor((bar - label.length) / 2)
  const chars = Array.from({ length: bar }, (_, i) =>
    i >= start && i < start + label.length ? label[i - start]! : ' ',
  )
  const out: Segment[] = []
  chars.forEach((ch, i) => {
    const isFilled = i < filled
    const last = out[out.length - 1]
    if (last && last.isFilled === isFilled) last.text += ch
    else out.push({ text: ch, isFilled })
  })
  return out
}

// 依可用寬度決定血條長度: 第二行 ctx + 資訊, 第三行 5h/7d; 所有血條等長, 太窄時先拿掉重置時間
export function layout(
  list: Gauge[],
  cols: number,
  info: string,
): { bar: number; showReset: boolean } {
  const limits = list.filter(g => g.label !== 'ctx')
  const hasCtx = list.some(g => g.label === 'ctx')
  const row2 = hasCtx ? cols - 4 - (info ? SEP.length + info.length : 0) : MAX_BAR
  const row3 = (showReset: boolean) => {
    if (limits.length === 0) return MAX_BAR
    const fixed =
      limits.reduce((sum, g) => sum + 4 + (showReset ? resetText(g).length : 0), 0) +
      SEP.length * (limits.length - 1)
    return Math.floor((cols - fixed) / limits.length)
  }
  const clampBar = (v: number) => Math.max(MIN_BAR, Math.min(MAX_BAR, v))

  if (row3(true) >= MIN_BAR + 2) {
    return { bar: clampBar(Math.min(row2, row3(true))), showReset: true }
  }
  return { bar: clampBar(Math.min(row2, row3(false))), showReset: false }
}

async function refreshModel($: EngineInterface) {
  const name = prettyModel(await $.session.model())
  await update($, model, () => name)
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

  // 主對話與子代理的每一輪都算進本 session 的 token
  on('turn.complete', async ($, e, next) => {
    const u = e.usage
    if (u) {
      await update($, tokens, t => ({
        input: t.input + u.input_tokens + u.cache_read_input_tokens + u.cache_creation_input_tokens,
        output: t.output + u.output_tokens,
      }))
    }
    return next(e)
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

    const { Box, Text } = $.ui.resolve(e)
    const { bar, showReset } = layout(list, e.props.bodyColumns, info)
    const now = Date.now()
    const ctx = list.find(g => g.label === 'ctx')
    const limits = list.filter(g => g.label !== 'ctx')

    const gauge = (g: Gauge, withSep: boolean) => {
      const left = hp(g.used)
      const color = hpColor(left)
      return (
        <Box key={g.label} flexDirection="row">
          {withSep ? <Text dimColor>{SEP}</Text> : null}
          <Text bold>{g.label.padEnd(3)} </Text>
          {segments(left, bar).map((seg, j) =>
            seg.isFilled ? (
              <Text key={`s${j}`} backgroundColor={color} color="black" bold>
                {seg.text}
              </Text>
            ) : (
              <Text key={`s${j}`} backgroundColor={EMPTY_BG} color="white">
                {seg.text}
              </Text>
            ),
          )}
          {showReset ? <Text dimColor>{resetText(g)}</Text> : null}
        </Box>
      )
    }

    return (
      <Box flexDirection="column">
        {name ? (
          <Box key="model" flexDirection="row">
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
        ) : null}
        <Box key="ctx-row" flexDirection="row">
          {ctx ? gauge(ctx, false) : null}
          {ctx ? <Text dimColor>{SEP}</Text> : null}
          <Text>{info}</Text>
        </Box>
        {/* 兩行血條之間空一行, 避免上下色塊黏在一起 */}
        {ctx && limits.length > 0 ? <Text key="gap"> </Text> : null}
        {limits.length > 0 ? (
          <Box key="limit-row" flexDirection="row">
            {limits.map((g, i) => gauge(g, i > 0))}
          </Box>
        ) : null}
      </Box>
    )
  })
}
