export type Gauge = { label: string; used: number; resetsAt?: string }
export type Tokens = { input: number; output: number }

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
    }
  }
}
