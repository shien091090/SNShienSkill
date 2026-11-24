// 進測版號與送審日: 版號問 GitLab 上的 Lobby repo, 送審日讀公開的 Google Sheet
import type { ReleaseEntry } from '../types'

export const LOBBY_REPO = 'https://git-game.yile808.com/lobbygroup/Lobby.git'
export const SUBMISSION_CSV =
  'https://docs.google.com/spreadsheets/d/1Zj2zg1ifRDeWRuIWA5ZRBhZj3zYeyZYEA3L3xgTYORs/export?format=csv&gid=1866154823'

// 送審日表已不公開, 改用訂版 skill(cli-prepare-release)的 service account 讀; 這個帳號已被共用到送審日表
export const SUBMISSION_SHEET_VALUES =
  'https://sheets.googleapis.com/v4/spreadsheets/1Zj2zg1ifRDeWRuIWA5ZRBhZj3zYeyZYEA3L3xgTYORs/values/Sheet1'
// 環境變數 GOOGLE_SHEETS_CREDENTIALS 沒設時的預設位置(訂版 skill 首次設定放的地方), 相對於家目錄
export const DEFAULT_CREDENTIALS = '.claude/credentials/client-agent-495603-66436678d81c.json'
export const TOKEN_URL = 'https://oauth2.googleapis.com/token'
const SHEETS_SCOPE = 'https://www.googleapis.com/auth/spreadsheets.readonly'

export type ServiceAccount = { client_email: string; private_key: string }

const b64url = (bytes: Uint8Array) => bytes.toBase64({ alphabet: 'base64url', omitPadding: true })
const b64urlJson = (value: unknown) => b64url(new TextEncoder().encode(JSON.stringify(value)))

// service account 的 JWT 宣告: 換 token 用, 有效 1 小時(Google 允許的上限)
export function jwtClaims(email: string, nowSec: number) {
  return { iss: email, scope: SHEETS_SCOPE, aud: TOKEN_URL, iat: nowSec, exp: nowSec + 3600 }
}

// PEM(PKCS#8) → 原始 bytes
export function pemToBytes(pem: string): Uint8Array {
  return Uint8Array.fromBase64(pem.replace(/-----[^-]+-----/g, '').replace(/\s+/g, ''))
}

// plugin 環境的 crypto.subtle 只有 digest, 沒有 importKey / sign, 所以 RSA 簽章用 BigInt 自己算

export type RsaKey = { n: bigint; d: bigint; p: bigint; q: bigint; dp: bigint; dq: bigint; qi: bigint }

const toBig = (bytes: Uint8Array) => bytes.length === 0 ? 0n : BigInt(`0x${bytes.toHex()}`)

// 讀一個 DER 元素: 回傳標籤、內容與下一個元素的位置
function derRead(buf: Uint8Array, at: number): { tag: number; body: Uint8Array; end: number } {
  const tag = buf[at]!
  let len = buf[at + 1]!
  let pos = at + 2
  if (len & 0x80) {
    const count = len & 0x7f
    len = 0
    for (let i = 0; i < count; i++) len = len * 256 + buf[pos + i]!
    pos += count
  }
  return { tag, body: buf.subarray(pos, pos + len), end: pos + len }
}

// 依序取出 SEQUENCE 內的元素
function derItems(seq: Uint8Array) {
  const items: { tag: number; body: Uint8Array }[] = []
  for (let at = 0; at < seq.length;) {
    const item = derRead(seq, at)
    items.push(item)
    at = item.end
  }
  return items
}

// PKCS#8 PrivateKeyInfo → 裡面的 RSAPrivateKey(n, e, d, p, q, dp, dq, qi)
export function parsePkcs8(der: Uint8Array): RsaKey {
  const info = derItems(derRead(der, 0).body)
  const rsa = derItems(derRead(info[2]!.body, 0).body).map(i => toBig(i.body))
  const [, n, , d, p, q, dp, dq, qi] = rsa
  return { n: n!, d: d!, p: p!, q: q!, dp: dp!, dq: dq!, qi: qi! }
}

function modPow(base: bigint, exp: bigint, mod: bigint): bigint {
  let result = 1n
  let b = base % mod
  for (let e = exp; e > 0n; e >>= 1n) {
    if (e & 1n) result = (result * b) % mod
    b = (b * b) % mod
  }
  return result
}

// SHA-256 的 DigestInfo 前綴(RFC 8017 9.2)
const SHA256_PREFIX = Uint8Array.fromHex('3031300d060960864801650304020105000420')

// RSASSA-PKCS1-v1_5 + SHA-256: EM = 00 01 FF..FF 00 DigestInfo, 再用 CRT 算 EM^d mod n
export async function rsaSign(key: RsaKey, data: Uint8Array): Promise<Uint8Array> {
  const k = key.n.toString(16).replace(/^0+/, '').length + 1 >> 1
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', data))
  const t = new Uint8Array([...SHA256_PREFIX, ...digest])
  const em = new Uint8Array(k).fill(0xff)
  em[0] = 0
  em[1] = 1
  em[k - t.length - 1] = 0
  em.set(t, k - t.length)
  const m = toBig(em)
  const m1 = modPow(m, key.dp, key.p)
  const m2 = modPow(m, key.dq, key.q)
  const h = (key.qi * ((m1 - m2) % key.p + key.p)) % key.p
  const s = m2 + h * key.q
  return Uint8Array.fromHex(s.toString(16).padStart(k * 2, '0'))
}

// 用 service account 私鑰簽 RS256 JWT
export async function signJwt(account: ServiceAccount, nowSec: number): Promise<string> {
  const head = `${b64urlJson({ alg: 'RS256', typ: 'JWT' })}.${b64urlJson(jwtClaims(account.client_email, nowSec))}`
  const sig = await rsaSign(parsePkcs8(pemToBytes(account.private_key)), new TextEncoder().encode(head))
  return `${head}.${b64url(sig)}`
}

// 從 plugins-src 載入的是維護者自家電腦; 其他(市集安裝)都算公司版
export const isCompanyEdition = (root: string) => !root.replace(/\\/g, '/').includes('/plugins-src/')

type VersionTag = { name: string; sha: string }
export type LsRemote = { masterSha: string | null; tags: VersionTag[] }

// 版號 tag: 3.141.4_Rev1、3.140.4_Rev1_Hotfix1; 其他(scg_0.2.4 等)不管
const TAG_RE = /^(\d+)\.(\d+)\.(\d+)(?:_Rev(\d+))?(?:_Hotfix(\d+))?/

export function parseLsRemote(text: string): LsRemote {
  let masterSha: string | null = null
  const tags = new Map<string, string>()
  for (const line of text.split('\n')) {
    const [sha, ref] = line.trim().split('\t')
    if (!sha || !ref) continue
    if (ref === 'refs/heads/master') masterSha = sha
    if (!ref.startsWith('refs/tags/')) continue
    const peeled = ref.endsWith('^{}')
    const name = ref.slice('refs/tags/'.length).replace(/\^\{\}$/, '')
    if (!TAG_RE.test(name)) continue
    // 附註 tag 指向 tag 物件本身, ^{} 那行才是實際的 commit
    if (peeled || !tags.has(name)) tags.set(name, sha)
  }
  return { masterSha, tags: [...tags].map(([name, sha]) => ({ name, sha })) }
}

const minorOf = (tag: string) => {
  const m = tag.match(TAG_RE)!
  return `${m[1]}.${m[2]}`
}

// 依 patch、Rev、Hotfix 的數字比大小
function tagRank(tag: string): number[] {
  const m = tag.match(TAG_RE)!
  return [3, 4, 5].map(i => Number(m[i] ?? 0))
}

function compareNums(a: number[], b: number[]): number {
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const d = (a[i] ?? 0) - (b[i] ?? 0)
    if (d !== 0) return d
  }
  return 0
}

const minorRank = (minor: string) => minor.split('.').map(Number)

// 送審日表(公開 CSV 匯出): 交給 parseSheetRows
export function parseSheet(csv: string, year: number): Record<string, string | null> {
  return parseSheetRows(csv.split(/\r?\n/).map(line => line.split(',')), year)
}

// 送審日表: 第一列是標題, 之後每列 [版本, 日期] → YYYY-MM-DD; 沒寫年份補今年, N/A 或讀不懂的是 null
export function parseSheetRows(rows: string[][], year: number): Record<string, string | null> {
  const result: Record<string, string | null> = {}
  for (const row of rows.slice(1)) {
    const [version, raw] = row.map(s => String(s ?? '').trim())
    if (!version || !/^\d+\.\d+$/.test(version)) continue
    const m = (raw ?? '').match(/^(?:(\d{4})\/)?(\d{1,2})\/(\d{1,2})$/)
    result[version] = m
      ? `${m[1] ?? year}-${m[2]!.padStart(2, '0')}-${m[3]!.padStart(2, '0')}`
      : null
  }
  return result
}

// master 最新 commit 上的 tag(沒有就沿用上次的), 加上比它新、打過 tag 且在送審日表上的版本
export function buildBoard(
  ls: LsRemote,
  sheet: Record<string, string | null>,
  lastMasterTag: string | null,
): { masterTag: string | null; current: ReleaseEntry | null; others: ReleaseEntry[] } {
  const latest = new Map<string, string>()
  for (const { name } of ls.tags) {
    const minor = minorOf(name)
    const prev = latest.get(minor)
    if (!prev || compareNums(tagRank(name), tagRank(prev)) > 0) latest.set(minor, name)
  }
  const onMaster = ls.tags.filter(t => t.sha === ls.masterSha).map(t => t.name)
  onMaster.sort((a, b) => compareNums([...minorRank(minorOf(b)), ...tagRank(b)], [...minorRank(minorOf(a)), ...tagRank(a)]))
  const masterTag = onMaster[0] ?? lastMasterTag
  if (!masterTag) return { masterTag: null, current: null, others: [] }
  const masterMinor = minorOf(masterTag)

  const entry = (minor: string): ReleaseEntry => ({ minor, tag: latest.get(minor) ?? '', date: sheet[minor] ?? null })
  const others = [...latest.keys()]
    // 只列送審日表上有的版本: 德撲等其他產品或打錯的 tag 不在表上
    .filter(minor => minor in sheet && compareNums(minorRank(minor), minorRank(masterMinor)) > 0)
    .sort((a, b) => compareNums(minorRank(a), minorRank(b)))
    .map(entry)
  // 同一個中版號底下 patch 更大的 tag 可能還沒進 master, 第一行要顯示 master 上那個
  return { masterTag, current: { ...entry(masterMinor), tag: masterTag }, others }
}

// 距離送審日還有幾天(以當地日期計算); 負數是已經過了
export function daysUntil(date: string, now: Date): number {
  const [y, m, d] = date.split('-').map(Number)
  const target = Date.UTC(y!, m! - 1, d!)
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())
  return Math.round((target - today) / 86_400_000)
}

export const shortDate = (date: string) => {
  const [, m, d] = date.split('-').map(Number)
  return `${m}/${d}`
}

