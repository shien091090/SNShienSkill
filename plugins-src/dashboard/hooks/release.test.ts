import { expect, test } from 'claude-code/testing'
import { buildBoard, daysUntil, isCompanyEdition, jwtClaims, parseLsRemote, parseSheet, parseSheetRows, parsePkcs8, rsaSign, shortDate, signJwt, TOKEN_URL } from './release'

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

test('master 最新 commit 有 tag: 第一行就是那個 tag, 同中版號 patch 更大但沒進 master 的不算', () => {
  const board = buildBoard(parseLsRemote(LS), parseSheet(CSV, 2026), null)
  expect(board.masterTag).toBe('3.140.7_Rev2')
  expect(board.current).toEqual({ minor: '3.140', tag: '3.140.7_Rev2', date: '2026-10-27' })
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

test('master 最新 commit 沒有 tag: 沿用上次的 tag; 從沒判斷過就是無法判定', () => {
  const ls = parseLsRemote(LS.replace(/^b66ee4f6\w+\trefs\/heads\/master/m, `${'9'.repeat(40)}\trefs/heads/master`))
  expect(buildBoard(ls, {}, '3.140.7_Rev2').current).toEqual({ minor: '3.140', tag: '3.140.7_Rev2', date: null })
  const unknown = buildBoard(ls, {}, null)
  expect(unknown.current).toBe(null)
  expect(unknown.others).toEqual([])
})

test('表上沒有的版本送審日是未定', () => {
  expect(buildBoard(parseLsRemote(LS), {}, null).current?.date).toBe(null)
})

test('patch 依數字比大小, 不是字串', () => {
  const onMaster = parseLsRemote(['a\trefs/heads/master', 'a\trefs/tags/3.150.9_Rev1', 'a\trefs/tags/3.150.10_Rev1'].join('\n'))
  expect(buildBoard(onMaster, {}, null).current?.tag).toBe('3.150.10_Rev1')
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

test('送審日表用 API 讀到的列與 CSV 解析結果一致', () => {
  const rows = [['Version', 'DateTime'], ['3.130', 'N/A'], ['3.140', '10/27'], ['3.142', '2026/11/30'], ['3.143']]
  expect(parseSheetRows(rows, 2026)).toEqual({ '3.130': null, '3.140': '2026-10-27', '3.142': '2026-11-30', '3.143': null })
})

// 測試專用的 1024 位元金鑰(只用在這裡, 不對應任何帳號); 簽章是用 Python cryptography 對同一把金鑰算出的標準答案
const TEST_KEY_DER = [
  'MIICdQIBADANBgkqhkiG9w0BAQEFAASCAl8wggJbAgEAAoGBAKlgWTTN9x/GvPd+',
  '1HY4awYLDijdk5YVIet7gXJMr+vkklzsT036BPWQd3M3kF/vIGAqV9pMQoTtRUQa',
  'konw4RFEZ84JCIlnKVUeCU8drupLM4v4x7yy7/4xyoDk8mdU/6V9aknvHMLYpH82',
  'BKeJwptKG1tHCQ7p3sw2cxhoX/brAgMBAAECgYBMyJ7oL08Omrvjvx12EpGCBdT/',
  'daOIcEAWTsEaHeXKnK41bfNtuCAzarCcDN5ofzFAJzH4hoXJWP8DpsAzxH1i57Ne',
  'MZfz1fi6Zznt6pLyyt90NGBfwzR2z5FwLdOfptJt6sOmlc6Ht+9su2oWqdzjIwTG',
  'HveEzGgqmu05JewZoQJBANVPFFsoExu6E29gZXi+ny3wFCNNeNOmQRoZsmZ8YQ/S',
  'KsDXtluB/u/4VmOoYnmXcoERmZh38GFy7jXizqaoYmMCQQDLRmCKYAKkmDd/cBW0',
  'lDi6XBo1A4bci8a+LdGemk4Tzb4KF2p/RuUl1zg4lL4TU35moxIuQEwdkR3kyPwg',
  '1XvZAkAhkeJ4PiRTtsMcQiV2DTnr9t6Ud7rORFn2i5jB/E0iOkc0Nj6ixCClD4Y5',
  'BOUKkcUZfvWXQzj3fSj0Hg+7tsBVAkBMxqMWAJde9YMYpgv8rXMTqE/ZsCBS0pRZ',
  'JlMjFWLiBfZ+N0PpGKzZ8wTwEfYMtJ9sQrFOOMjG7hWdYPAhsqBZAkBpvi7ROGif',
  '7rml4bx8Oa0y5KGmq4a9R6zsfnKGyc3tHK3oZ7+ojT1GAxrQJfpT9kq6oFfikVhl',
  'nE+seyeBqsDz',
].join('')
const TEST_SIG = '081812a27bae39af64281c08696fec907981610a5064f2fc3629189986d33d1eb58d403c096f010aed7c2140f536e6df73cd1a8b5318c0360780f56ab1e806e5594088c5803ad550adf26fa70f7ddeafbafeba252b0b42d45f67d1a8f6756ccd2d1c18abd0c0a853b72058eafc8773e7df63c4f2485c0c14d6ba71aa5cb30b96'

test('RSA 簽章與標準實作一致(RSASSA-PKCS1-v1_5 + SHA-256)', async () => {
  const key = parsePkcs8(Uint8Array.fromBase64(TEST_KEY_DER))
  const sig = await rsaSign(key, new TextEncoder().encode('dashboard-test'))
  expect(sig.toHex()).toBe(TEST_SIG)
})

test('service account JWT: 三段式, 宣告帶唯讀 scope 與 1 小時效期, 簽在前兩段上', async () => {
  const pem = `-----BEGIN PRIVATE KEY-----\n${TEST_KEY_DER.replace(/(.{64})/g, '$1\n')}\n-----END PRIVATE KEY-----\n`
  const jwt = await signJwt({ client_email: 'bot@example.iam.gserviceaccount.com', private_key: pem }, 1_000)
  const [head, body, sig] = jwt.split('.')
  const claims = JSON.parse(new TextDecoder().decode(Uint8Array.fromBase64(body!, { alphabet: 'base64url' })))
  expect(claims).toEqual(jwtClaims('bot@example.iam.gserviceaccount.com', 1_000))
  expect(claims.aud).toBe(TOKEN_URL)
  expect(claims.exp - claims.iat).toBe(3600)
  const expected = await rsaSign(parsePkcs8(Uint8Array.fromBase64(TEST_KEY_DER)), new TextEncoder().encode(`${head}.${body}`))
  expect(Uint8Array.fromBase64(sig!, { alphabet: 'base64url' }).toHex()).toBe(expected.toHex())
})
