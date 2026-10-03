import { expect, test } from 'claude-code/testing'
import { hp, hpColor, layout, modelWidth, prettyModel, resetText, segments, SEP, shimmer, spinnerAt, toGauges } from './register'

const sample = toGauges(
  [
    { kind: 'five_hour', percentUsed: 40, resetsAt: '2026-10-04T18:00:00' },
    { kind: 'seven_day', percentUsed: 10, resetsAt: '2026-10-09T08:00:00' },
  ],
  { window: 200000, tokens: 50000, percent: 25 },
)

// 實際畫出來的一列寬度, 與 register.tsx 的排版一致
function rowWidth(cols: number): number {
  const { bar, showReset } = layout(sample, cols)
  return (
    sample.reduce((sum, g) => sum + 4 + bar + (showReset ? resetText(g).length : 0), 0) +
    SEP.length * (sample.length - 1)
  )
}

test('血量是 100 減已用, 夾在範圍內', () => {
  expect(hp(23.5)).toBe(76.5)
  expect(hp(120)).toBe(0)
  expect(hp(-5)).toBe(100)
})

test('血量顏色依剩餘量變化', () => {
  expect(hpColor(80)).toBe('green')
  expect(hpColor(30)).toBe('yellow')
  expect(hpColor(10)).toBe('red')
})

test('排序為 ctx、5h、7d', () => {
  expect(sample.map(x => x.label)).toEqual(['ctx', '5h', '7d'])
})

test('重置時間: 5h 顯示時分, 7d 顯示月日', () => {
  expect(resetText(sample[1]!)).toBe(' ↻ 18:00')
  expect(resetText(sample[2]!)).toBe(' ↻ 10/9')
  expect(resetText(sample[0]!)).toBe('')
})

test('半寬視窗(80、95 欄)放得下一列, 且顯示重置時間', () => {
  for (const cols of [80, 95]) {
    expect(rowWidth(cols)).toBeLessThanOrEqual(cols)
    expect(layout(sample, cols).showReset).toBe(true)
  }
})

test('更窄時先拿掉重置時間', () => {
  expect(layout(sample, 50).showReset).toBe(false)
  expect(rowWidth(50)).toBeLessThanOrEqual(50)
})

test('寬視窗血條不會無限拉長', () => {
  expect(layout(sample, 300).bar).toBe(14)
})

test('%數置中疊在血條上, 填滿與未填滿分段', () => {
  const segs = segments(50, 10)
  expect(segs.map(s => s.text).join('')).toBe('   50%    ')
  expect(segs).toEqual([
    { text: '   50', isFilled: true },
    { text: '%    ', isFilled: false },
  ])
  expect(segments(100, 6).map(s => s.text).join('')).toBe(' 100% ')
  expect(segments(0, 6).every(s => !s.isFilled)).toBe(true)
})

test('模型識別字轉成好讀的名字', () => {
  expect(prettyModel('claude-opus-5-5')).toBe('Opus 5.5')
  expect(prettyModel('claude-opus-5-5[1m]')).toBe('Opus 5.5')
  expect(prettyModel('claude-haiku-4-5-20251001')).toBe('Haiku 4.5')
  expect(prettyModel('Opus 5.5')).toBe('Opus 5.5')
})

test('亮光每個字一個顏色, 且會隨時間移動', () => {
  const a = shimmer('Opus 5.5', 0)
  const b = shimmer('Opus 5.5', 400)
  expect(a.length).toBe(8)
  expect(a.every(c => /^#[0-9a-f]{6}$/.test(c))).toBe(true)
  expect(a).not.toEqual(b)
  expect(spinnerAt(0)).not.toBe(spinnerAt(100))
})

test('加上模型名字後半寬視窗仍放得下一列', () => {
  const extra = modelWidth('Opus 5.5')
  const { bar, showReset } = layout(sample, 80, extra)
  const width =
    extra +
    sample.reduce((sum, g) => sum + 4 + bar + (showReset ? resetText(g).length : 0), 0) +
    SEP.length * (sample.length - 1)
  expect(width).toBeLessThanOrEqual(80)
  expect(showReset).toBe(true)
})
