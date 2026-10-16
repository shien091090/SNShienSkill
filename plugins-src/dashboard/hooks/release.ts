// 進測版號與送審日: 版號問 GitLab 上的 Lobby repo, 送審日讀公開的 Google Sheet
import type { ReleaseEntry } from '../types'

export const LOBBY_REPO = 'https://git-game.yile808.com/lobbygroup/Lobby.git'
export const SUBMISSION_CSV =
  'https://docs.google.com/spreadsheets/d/1Zj2zg1ifRDeWRuIWA5ZRBhZj3zYeyZYEA3L3xgTYORs/export?format=csv&gid=1866154823'

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

// 送審日表: 版本 → YYYY-MM-DD; 沒寫年份補今年, N/A 或讀不懂的是 null
export function parseSheet(csv: string, year: number): Record<string, string | null> {
  const result: Record<string, string | null> = {}
  for (const line of csv.split(/\r?\n/).slice(1)) {
    const [version, raw] = line.split(',').map(s => s.trim())
    if (!version || !/^\d+\.\d+$/.test(version)) continue
    const m = (raw ?? '').match(/^(?:(\d{4})\/)?(\d{1,2})\/(\d{1,2})$/)
    result[version] = m
      ? `${m[1] ?? year}-${m[2]!.padStart(2, '0')}-${m[3]!.padStart(2, '0')}`
      : null
  }
  return result
}

// master 的中版號(master 最新 commit 上的 tag, 沒有就沿用上次的), 加上比它新、打過 tag 且在送審日表上的版本
export function buildBoard(
  ls: LsRemote,
  sheet: Record<string, string | null>,
  lastMasterMinor: string | null,
): { masterMinor: string | null; current: ReleaseEntry | null; others: ReleaseEntry[] } {
  const latest = new Map<string, string>()
  for (const { name } of ls.tags) {
    const minor = minorOf(name)
    const prev = latest.get(minor)
    if (!prev || compareNums(tagRank(name), tagRank(prev)) > 0) latest.set(minor, name)
  }
  const onMaster = ls.tags.filter(t => t.sha === ls.masterSha).map(t => minorOf(t.name))
  onMaster.sort((a, b) => compareNums(minorRank(b), minorRank(a)))
  const masterMinor = onMaster[0] ?? lastMasterMinor
  if (!masterMinor) return { masterMinor: null, current: null, others: [] }

  const entry = (minor: string): ReleaseEntry => ({ minor, tag: latest.get(minor) ?? '', date: sheet[minor] ?? null })
  const others = [...latest.keys()]
    // 只列送審日表上有的版本: 德撲等其他產品或打錯的 tag 不在表上
    .filter(minor => minor in sheet && compareNums(minorRank(minor), minorRank(masterMinor)) > 0)
    .sort((a, b) => compareNums(minorRank(a), minorRank(b)))
    .map(entry)
  return { masterMinor, current: entry(masterMinor), others }
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

