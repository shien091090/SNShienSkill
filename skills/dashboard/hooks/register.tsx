import { atom, read, update } from 'claude-code'
import type { Register, SessionContextUsage, SessionRateLimit } from 'claude-code'

import type { Gauge } from '../types'

const gauges = atom({ plugin: 'dashboard', key: 'gauges' } as const, [] as Gauge[])

const LABELS: Record<string, string> = {
  five_hour: '5h',
  seven_day: '7d',
  spend_limit: '$$',
}
const ORDER = ['ctx', '5h', '7d']

// 區塊之間的分隔線
export const SEP = ' │ '
const MIN_BAR = 6
const MAX_BAR = 14
const EMPTY_BG = '#3a3a3a'

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

// 依可用寬度決定血條長度(三條等長), 太窄時先拿掉重置時間
export function layout(list: Gauge[], cols: number): { bar: number; showReset: boolean } {
  const fixed = (showReset: boolean) =>
    list.reduce((sum, g) => sum + 4 + (showReset ? resetText(g).length : 0), 0) +
    SEP.length * Math.max(0, list.length - 1)
  const barFor = (showReset: boolean) =>
    Math.floor((cols - fixed(showReset)) / Math.max(1, list.length))

  const withReset = barFor(true)
  if (withReset >= MIN_BAR + 2) {
    return { bar: Math.min(MAX_BAR, withReset), showReset: true }
  }
  return { bar: Math.max(MIN_BAR, Math.min(MAX_BAR, barFor(false))), showReset: false }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const result = await next(e)
    const u = await $.session.usage()
    await update($, gauges, () => toGauges(u.rateLimits, u.context))
    return result
  })

  on('session.measure', async ($, e, next) => {
    await update($, gauges, () => toGauges(e.rateLimits, e.context))
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const list = await read($, gauges)
    if (e.props.hasSurvey || list.length === 0) {
      return next(e)
    }

    const { Box, Text } = $.ui.resolve(e)
    const { bar, showReset } = layout(list, e.props.bodyColumns)

    return (
      <Box flexDirection="row">
        {list.map((g, i) => {
          const left = hp(g.used)
          const color = hpColor(left)
          return (
            <Box key={g.label} flexDirection="row">
              {i > 0 ? <Text dimColor>{SEP}</Text> : null}
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
        })}
      </Box>
    )
  })
}
