import { expect, test } from 'claude-code/testing'
import { fmtDuration, folderName, preview, toastText } from './register'

test('耗時格式', () => {
  expect(fmtDuration(4_200)).toBe('4s')
  expect(fmtDuration(83_000)).toBe('1m23s')
})

test('預覽取第一段非空文字並去掉 markdown 符號', () => {
  expect(preview('\n## **完成了**\n細節')).toBe('完成了')
  expect(preview('a'.repeat(100)).length).toBe(80)
  expect(preview('')).toBe('')
})

test('資料夾名稱', () => {
  expect(folderName('D:\\Git\\MYS-808')).toBe('MYS-808')
  expect(folderName('/home/u/proj/')).toBe('proj')
})

test('通知標題依結束原因變化', () => {
  expect(toastText('answer', '好了', 5000, 'C:\\Users\\user').title).toBe('Claude 回應完成')
  expect(toastText('aborted', '', 5000, 'C:\\Users\\user').title).toBe('Claude 已中斷')
  expect(toastText('error', '', 5000, 'C:\\Users\\user').title).toBe('Claude 出錯了')
  expect(toastText('answer', '好了', 5000, 'C:\\Users\\user').body).toBe('user · 5s\n好了')
})
