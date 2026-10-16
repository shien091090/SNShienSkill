import { expect, test } from 'claude-code/testing'
import { buildBoard, daysUntil, isCompanyEdition, parseLsRemote, parseSheet, shortDate } from './release'

const LS = [
  'b66ee4f6bdeccebf197167959e48955850b4badb\trefs/heads/master',
  '1111111111111111111111111111111111111111\trefs/tags/3.140.7_Rev1',
  'd38c14fe888aaaaaaaaaaaaaaaaaaaaaaaaaaaaa\trefs/tags/3.140.7_Rev1^{}',
  '2222222222222222222222222222222222222222\trefs/tags/3.140.7_Rev2',
  'b66ee4f6bdeccebf197167959e48955850b4badb\trefs/tags/3.140.7_Rev2^{}',
  '3333333333333333333333333333333333333333\trefs/tags/3.140.10_Rev1_Hotfix1',
  '4444444444444444444444444444444444444444\trefs/tags/3.141.3_Rev4',
  '5555555555555555555555555555555555555555\trefs/tags/3.141.4_Rev1',
  '6666666666666666666666666666666666666666\trefs/tags/3.139.117_Rev4',
  '7777777777777777777777777777777777777777\trefs/tags/scg_0.2.4',
  '8888888888888888888888888888888888888888\trefs/heads/feature/3.142',
].join('\n')

const CSV = 'Version,DateTime\r\n3.130,N/A\r\n3.139,2026/10/08\r\n3.140,10/27\r\n3.141,11/16\r\n3.142,11/30\r\n'

test('ls-remote: 取出 master 指向的 commit 與版號 tag, 附註 tag 以 ^{} 的 commit 為準', () => {
  const ls = parseLsRemote(LS)
  expect(ls.masterSha).toBe('b66ee4f6bdeccebf197167959e48955850b4badb')
  expect(ls.tags.find(t => t.name === '3.140.7_Rev2')?.sha).toBe('b66ee4f6bdeccebf197167959e48955850b4badb')
  expect(ls.tags.some(t => t.name === 'scg_0.2.4')).toBe(false)
})

test('送審日: 沒有年份補今年, N/A 當作未定, 個位數月日也讀得懂', () => {
  const sheet = parseSheet('Version,DateTime\n3.132,2026/06/8\n3.140,10/27\n3.130,N/A\n', 2026)
  expect(sheet['3.132']).toBe('2026-06-08')
  expect(sheet['3.140']).toBe('2026-10-27')
  expect(sheet['3.130']).toBe(null)
})

test('master 最新 commit 有 tag: 用它的中版號, 括號是該版最新的 tag', () => {
  const board = buildBoard(parseLsRemote(LS), parseSheet(CSV, 2026), null)
  expect(board.masterMinor).toBe('3.140')
  expect(board.current).toEqual({ minor: '3.140', tag: '3.140.10_Rev1_Hotfix1', date: '2026-10-27' })
  expect(board.others).toEqual([{ minor: '3.141', tag: '3.141.4_Rev1', date: '2026-11-16' }])
})

test('只有分支沒有 tag 的版本不算進測; 比 master 舊的也不算', () => {
  const board = buildBoard(parseLsRemote(LS), parseSheet(CSV, 2026), null)
  expect(board.others.map(o => o.minor)).toEqual(['3.141'])
})

test('送審日表上沒有的版本不算進測: 德撲或打錯的 tag', () => {
  const ls = parseLsRemote(LS + '\n9\trefs/tags/3.950.1_Rev5\n9\trefs/tags/4.138.899_Rev1')
  expect(buildBoard(ls, parseSheet(CSV, 2026), null).others.map(o => o.minor)).toEqual(['3.141'])
})

test('master 最新 commit 沒有 tag: 沿用上次的中版號; 從沒判斷過就是無法判定', () => {
  const ls = parseLsRemote(LS.replace(/^b66ee4f6\w+\trefs\/heads\/master/m, `${'9'.repeat(40)}\trefs/heads/master`))
  expect(buildBoard(ls, {}, '3.140').current?.minor).toBe('3.140')
  const unknown = buildBoard(ls, {}, null)
  expect(unknown.current).toBe(null)
  expect(unknown.others).toEqual([])
})

test('表上沒有的版本送審日是未定', () => {
  expect(buildBoard(parseLsRemote(LS), {}, null).current?.date).toBe(null)
})

test('patch 依數字比大小, 不是字串', () => {
  const ls = parseLsRemote(['a\trefs/heads/master', 'a\trefs/tags/3.150.9_Rev1', 'b\trefs/tags/3.150.10_Rev1'].join('\n'))
  expect(buildBoard(ls, {}, null).current?.tag).toBe('3.150.10_Rev1')
})

test('剩幾天以當地日期計算, 日期顯示成 月/日', () => {
  const now = new Date(2026, 9, 16, 23, 30)
  expect(daysUntil('2026-10-27', now)).toBe(11)
  expect(daysUntil('2026-10-16', now)).toBe(0)
  expect(daysUntil('2026-10-14', now)).toBe(-2)
  expect(shortDate('2026-10-07')).toBe('10/7')
})

test('從 plugins-src 載入的是自家電腦, 其他都算公司版', () => {
  expect(isCompanyEdition('C:\\Users\\me\\.claude\\plugins-src\\dashboard')).toBe(false)
  expect(isCompanyEdition('C:\\Users\\me\\.claude\\plugins\\cache\\lobby-agent-client\\dashboard\\1.1.0')).toBe(true)
})
