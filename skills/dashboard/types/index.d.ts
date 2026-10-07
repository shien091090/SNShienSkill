export type Gauge = { label: string; used: number; resetsAt?: string }
export type Tokens = { input: number; output: number }
export type UnityProject = { name: string; path: string }

declare module 'claude-code' {
  interface PluginState {
    dashboard: {
      gauges: Gauge[]
      model: string
      tokens: Tokens
      cost: number | null
      title: string
      pendingTitle: string | null
      isEditing: boolean
      transcriptPath: string
      isAutoTitle: boolean
      isMenuOpen: boolean
      isRemoteOn: boolean
      todos: string[]
      unityProject: UnityProject | null
    }
  }
}
