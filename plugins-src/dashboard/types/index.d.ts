export type Gauge = { label: string; used: number; resetsAt?: string }
export type Tokens = { input: number; output: number }
export type UnityProject = { name: string; path: string }
// 進測中的一個版本: 中版號、該版最新 tag、送審日(YYYY-MM-DD, 未定是 null)
export type ReleaseEntry = { minor: string; tag: string; date: string | null }
// current 是 master 的版本(無法判定時 null); fetchedAt 是最後一次抓成功的時間, isStale 表示之後抓失敗
export type ReleaseBoard = { current: ReleaseEntry | null; others: ReleaseEntry[]; fetchedAt: number; isStale: boolean }

declare module 'claude-code' {
  interface PluginState {
    dashboard: {
      gauges: Gauge[]
      model: string
      tokens: Tokens
      cost: number | null
      title: string
      isEditing: boolean
      transcriptPath: string
      isAutoTitle: boolean
      isMenuOpen: boolean
      isModelMenuOpen: boolean
      isRemoteOn: boolean
      todos: string[]
      unityProject: UnityProject | null
      release: ReleaseBoard | null
    }
  }
}
