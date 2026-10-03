export type Gauge = { label: string; used: number; resetsAt?: string }

declare module 'claude-code' {
  interface PluginState {
    dashboard: { gauges: Gauge[]; model: string }
  }
}
