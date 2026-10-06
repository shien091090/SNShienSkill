import { expect, mock, test } from 'claude-code/testing'
import { folderName, taskSummary, toastText } from './notify'
import { latestTitle, strWidth, fmtTokens, hp, hpColor, infoText, layout, pctText, prettyModel, QUICK_ACTIONS, resetText, SAVE_STATE_PROMPT, SEP, shimmer, spinnerAt, toGauges } from './register'

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
  const row2 = 4 + bar + 5 + pad + SEP.length + strWidth(INFO)
  const row3 =
    limits.reduce((sum, g) => sum + 4 + bar + 5 + (showReset ? resetText(g).length : 0), 0) +
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
  expect(layout(sample, 300, INFO).bar).toBe(12)
})

test('%數固定 5 格寬', () => {
  expect(pctText(5)).toBe('   5%')
  expect(pctText(79.4)).toBe('  79%')
  expect(pctText(100)).toBe(' 100%')
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
    const row2Sep = 4 + bar + 5 + pad
    const row3Sep = 4 + bar + 5 + (showReset ? resetText(limits[0]!).length : 0)
    expect(row2Sep).toBe(row3Sep)
  }
})

const PROPS = {
  hasSurvey: false,
  isWorking: false,
  maxRows: 10,
  bodyColumns: 80,
  scroll: { offset: 0, bodyRows: 10 },
  view: {},
}

test('改名按鈕: 按下出現輸入框, 送出後名稱顯示在模型旁邊', async ($, on) => {
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('session.model', () => ({ value: 'claude-opus-5-5' }))
  on('session.usage', () => ({ value: { startedAt: 0, context: { window: 200000 }, rateLimits: [] } }))
  await $.session.start({ cwd: 'C:\proj', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ plugin: 'dashboard', surface: 'terminal', component: 'AbovePrompt', props: PROPS })
  expect((await ui.find({ key: 'title-input' }))).toBeUndefined()
  await ui.press({ key: 'title-rename' })
  expect(await ui.find({ key: 'title-input' })).toBeDefined()
  await ui.input({ key: 'title-input', text: '資格賽修正' })
  expect(await ui.find({ key: 'title-input' })).toBeUndefined()
  expect(await ui.find({ text: '資格賽修正' })).toBeDefined()
})

test('從對話紀錄讀名稱: 手動改的優先, 其次是最新的 AI 標題', () => {
  const ai = (t: string) => JSON.stringify({ type: 'ai-title', aiTitle: t })
  const custom = (t: string) => JSON.stringify({ type: 'custom-title', customTitle: t })
  const msg = JSON.stringify({ type: 'user', message: 'hi' })
  expect(latestTitle([msg, ai('舊標題'), msg, ai('新標題')].join('\n'))).toEqual({ title: '新標題', isAuto: true })
  expect(latestTitle([ai('AI 標題'), custom('我取的'), ai('之後的 AI 標題')].join('\n'))).toEqual({
    title: '我取的',
    isAuto: false,
  })
  expect(latestTitle(msg)).toBeNull()
  expect(latestTitle('{"type":"ai-title","aiTi')).toBeNull()
})

test('通知內文: 回覆段落接成一段, 去掉 markdown 符號, 太長截斷', () => {
  expect(taskSummary('## 完成\n\n- 改好**按鈕**\n- 加上測試')).toBe('完成 改好按鈕 加上測試')
  expect(taskSummary('字'.repeat(200)).length).toBe(90)
})

test('通知標題是 session 名稱, 沒有名稱時用資料夾名', () => {
  expect(toastText('資格賽修正', 'D:\\Git\\MYS-808', 'answer', '好了').title).toBe('資格賽修正')
  expect(toastText('', 'D:\\Git\\MYS-808', 'answer', '好了').title).toBe('未命名 · MYS-808')
  expect(folderName('/home/u/proj/')).toBe('proj')
})

test('通知內文依結束原因加上狀態', () => {
  expect(toastText('a', 'c', 'answer', '改好了').body).toBe('改好了')
  expect(toastText('a', 'c', 'aborted', '').body).toBe('已中斷')
  expect(toastText('a', 'c', 'error', '連線失敗').body).toBe('出錯了: 連線失敗')
  expect(toastText('a', 'c', 'answer', '').body).toBe('回應完成')
})

test('用 /model 換模型後, 不必送出訊息, 儀表板一秒內就換成新名字', async ($, on) => {
  const clock = mock.clock(on)
  let current = 'claude-sonnet-5'
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('session.model', () => ({ value: current }))
  on('session.usage', () => ({ value: { startedAt: 0, context: { window: 200000 }, rateLimits: [] } }))
  await $.session.start({ cwd: 'C:\proj', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ plugin: 'dashboard', surface: 'terminal', component: 'AbovePrompt', props: PROPS })
  expect(await ui.find({ text: 'Sonnet 5' })).toBeDefined()
  current = 'claude-opus-5-5'
  await clock.advance(1_000)
  expect(await ui.find({ text: 'Opus 5.5' })).toBeDefined()
})

for (const surface of ['terminal', 'desktop'] as const) {
  test(`${surface}: 快捷按鈕展開後, 記憶工作狀態送出 prompt、啟動RemoteControl 執行指令`, async ($, on) => {
    const prompts: string[] = []
    const commands: string[] = []
    on('session.start', (_, e) => ({ cwd: e.cwd }))
    on('session.model', () => ({ value: 'claude-opus-5-5' }))
    on('session.usage', () => ({ value: { startedAt: 0, context: { window: 200000 }, rateLimits: [] } }))
    on('prompt.submit', (_, e) => {
      prompts.push(e.text)
      return { text: e.text } as never
    })
    on('command.run', (_, e) => {
      commands.push(e.command)
      return { text: '' }
    })
    await $.session.start({ cwd: 'C:\proj', surface, isInteractive: true })
    const ui = await $.ui.mount({ plugin: 'dashboard', surface, component: 'AbovePrompt', props: PROPS })

    expect(await ui.find({ key: 'quick-save-state' })).toBeUndefined()
    await ui.press({ key: 'quick-toggle' })
    for (const a of QUICK_ACTIONS) expect(await ui.find({ key: a.key })).toBeDefined()

    await ui.press({ key: 'quick-save-state' })
    expect(prompts).toEqual([SAVE_STATE_PROMPT])
    expect(await ui.find({ key: 'quick-save-state' })).toBeUndefined()

    await ui.press({ key: 'quick-toggle' })
    await ui.press({ key: 'quick-remote-control' })
    expect(commands).toEqual(['remote-control'])
  })

  test(`${surface}: 按啟動RemoteControl 後按鈕改成 RemoteControl 狀態`, async ($, on) => {
    on('session.start', (_, e) => ({ cwd: e.cwd }))
    on('session.model', () => ({ value: 'claude-opus-5-5' }))
    on('session.usage', () => ({ value: { startedAt: 0, context: { window: 200000 }, rateLimits: [] } }))
    on('command.run', () => ({ text: '' }))
    await $.session.start({ cwd: 'C:\proj', surface, isInteractive: true })
    const ui = await $.ui.mount({ plugin: 'dashboard', surface, component: 'AbovePrompt', props: PROPS })

    await ui.press({ key: 'quick-toggle' })
    expect(await ui.find({ text: '啟動RemoteControl' })).toBeDefined()
    await ui.press({ key: 'quick-remote-control' })
    await ui.press({ key: 'quick-toggle' })
    expect(await ui.find({ text: 'RemoteControl 狀態' })).toBeDefined()
    expect(await ui.find({ text: '啟動RemoteControl' })).toBeUndefined()
  })

  test(`${surface}: 自己打 /remote-control 後按鈕也改成 RemoteControl 狀態`, async ($, on) => {
    on('session.start', (_, e) => ({ cwd: e.cwd }))
    on('session.model', () => ({ value: 'claude-opus-5-5' }))
    on('session.usage', () => ({ value: { startedAt: 0, context: { window: 200000 }, rateLimits: [] } }))
    on('command.run', () => ({ text: '' }))
    await $.session.start({ cwd: 'C:\proj', surface, isInteractive: true })
    await $.command.run({ command: 'remote-control' })
    const ui = await $.ui.mount({ plugin: 'dashboard', surface, component: 'AbovePrompt', props: PROPS })
    await ui.press({ key: 'quick-toggle' })
    expect(await ui.find({ text: 'RemoteControl 狀態' })).toBeDefined()
  })

  test(`${surface}: 按鈕進狀態面板斷開後, 按鈕改回啟動RemoteControl`, async ($, on) => {
    on('session.start', (_, e) => ({ cwd: e.cwd }))
    on('session.model', () => ({ value: 'claude-opus-5-5' }))
    on('session.usage', () => ({ value: { startedAt: 0, context: { window: 200000 }, rateLimits: [] } }))
    const outputs = ['', 'Remote Control disconnected.']
    on('command.run', () => ({ text: outputs.shift() ?? '' }))
    await $.session.start({ cwd: 'C:\proj', surface, isInteractive: true })
    const ui = await $.ui.mount({ plugin: 'dashboard', surface, component: 'AbovePrompt', props: PROPS })

    await ui.press({ key: 'quick-toggle' })
    await ui.press({ key: 'quick-remote-control' })
    await ui.press({ key: 'quick-toggle' })
    expect(await ui.find({ text: 'RemoteControl 狀態' })).toBeDefined()
    await ui.press({ key: 'quick-remote-control' })
    await ui.press({ key: 'quick-toggle' })
    expect(await ui.find({ text: '啟動RemoteControl' })).toBeDefined()
  })

  test(`${surface}: 自己打 /remote-control 斷開後, 按鈕也改回啟動RemoteControl`, async ($, on) => {
    on('session.start', (_, e) => ({ cwd: e.cwd }))
    on('session.model', () => ({ value: 'claude-opus-5-5' }))
    on('session.usage', () => ({ value: { startedAt: 0, context: { window: 200000 }, rateLimits: [] } }))
    const outputs = ['', 'Remote Control disconnected.']
    on('command.run', () => ({ text: outputs.shift() ?? '' }))
    await $.session.start({ cwd: 'C:\proj', surface, isInteractive: true })
    await $.command.run({ command: 'remote-control' })
    await $.command.run({ command: 'remote-control' })
    const ui = await $.ui.mount({ plugin: 'dashboard', surface, component: 'AbovePrompt', props: PROPS })
    await ui.press({ key: 'quick-toggle' })
    expect(await ui.find({ text: '啟動RemoteControl' })).toBeDefined()
  })
}
