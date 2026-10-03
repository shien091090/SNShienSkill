import { expect, test } from 'claude-code/testing'
import { strWidth, fmtTokens, hp, hpColor, infoText, layout, prettyModel, resetText, segments, SEP, shimmer, spinnerAt, toGauges } from './register'

const sample = toGauges(
  [
    { kind: 'five_hour', percentUsed: 40, resetsAt: '2026-10-04T18:00:00' },
    { kind: 'seven_day', percentUsed: 10, resetsAt: '2026-10-09T08:00:00' },
  ],
  { window: 200000, tokens: 50000, percent: 25 },
)

const INFO = infoText({ input: 1_234_567, output: 45_600 }, 3.21)

// 第二、三行實際畫出來的寬度, 與 register.tsx 的排版一致
function rowWidths(cols: number): [number, number] {
  const { bar, showReset, pad } = layout(sample, cols, INFO)
  const limits = sample.filter(g => g.label !== 'ctx')
  const row2 = 4 + bar + pad + SEP.length + strWidth(INFO)
  const row3 =
    limits.reduce((sum, g) => sum + 4 + bar + (showReset ? resetText(g).length : 0), 0) +
    SEP.length * (limits.length - 1)
  return [row2, row3]
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

test('半寬視窗(80、95 欄)每行都放得下, 且顯示重置時間', () => {
  for (const cols of [80, 95]) {
    for (const w of rowWidths(cols)) expect(w).toBeLessThanOrEqual(cols)
    expect(layout(sample, cols, INFO).showReset).toBe(true)
  }
})

test('更窄時先拿掉重置時間', () => {
  expect(layout(sample, 40, INFO).showReset).toBe(false)
})

test('寬視窗血條不會無限拉長', () => {
  expect(layout(sample, 300, INFO).bar).toBe(20)
})

test('%數置中嵌在細條內, 依填滿範圍分段', () => {
  const segs = segments(50, 12)
  expect(segs.map(x => x.text).join('')).toBe('▄▄▄ 50% ▄▄▄▄')
  expect(segs.map(x => [x.isFilled, x.isLabel])).toEqual([
    [true, false],
    [true, true],
    [false, true],
    [false, false],
  ])
  expect(segments(100, 8).map(x => x.text).join('')).toBe('▄ 100% ▄')
  expect(segments(0, 8).every(x => !x.isFilled)).toBe(true)
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

test('token 數縮寫', () => {
  expect(fmtTokens(950)).toBe('950')
  expect(fmtTokens(12_345)).toBe('12.3k')
  expect(fmtTokens(2_000)).toBe('2k')
  expect(fmtTokens(1_234_567)).toBe('1.2M')
})

test('資訊文字: token 與預估金額, 沒有金額時只顯示 token', () => {
  expect(INFO).toBe(`Token消耗 in 1.2M  out 45.6k${SEP}~$3.21`)
  expect(infoText({ input: 0, output: 0 }, null)).toBe('Token消耗 in 0  out 0')
})

test('中文字佔 2 格寬', () => {
  expect(strWidth('Token消耗')).toBe(9)
  expect(strWidth('abc')).toBe(3)
})

test('第二行分隔線與第三行第一個分隔線對齊', () => {
  for (const cols of [80, 95]) {
    const { bar, showReset, pad } = layout(sample, cols, INFO)
    const limits = sample.filter(g => g.label !== 'ctx')
    const row2Sep = 4 + bar + pad
    const row3Sep = 4 + bar + (showReset ? resetText(limits[0]!).length : 0)
    expect(row2Sep).toBe(row3Sep)
  }
})
