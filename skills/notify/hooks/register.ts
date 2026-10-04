import type { Register } from 'claude-code'

// 用 PowerShell 呼叫 Windows 通知; 標題與內文走環境變數, 避免引號跳脫問題
const TOAST_SCRIPT = `
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$texts = $xml.GetElementsByTagName('text')
$texts.Item(0).AppendChild($xml.CreateTextNode($env:CC_TOAST_TITLE)) > $null
$texts.Item(1).AppendChild($xml.CreateTextNode($env:CC_TOAST_BODY)) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
`

const PREVIEW_CHARS = 80

export function fmtDuration(ms: number): string {
  const sec = Math.round(ms / 1000)
  if (sec < 60) return `${sec}s`
  return `${Math.floor(sec / 60)}m${String(sec % 60).padStart(2, '0')}s`
}

// 回覆的第一段非空文字, 去掉 markdown 符號, 太長就截斷
export function preview(answer: string): string {
  const line =
    answer
      .split('\n')
      .map(l => l.replace(/[#*`>_|]/g, '').trim())
      .find(l => l.length > 0) ?? ''
  return line.length > PREVIEW_CHARS ? line.slice(0, PREVIEW_CHARS - 1) + '…' : line
}

export function folderName(cwd: string): string {
  return cwd.split(/[\\/]/).filter(Boolean).pop() ?? cwd
}

export function toastText(
  reason: string,
  answer: string,
  durationMs: number,
  cwd: string,
): { title: string; body: string } {
  const title =
    reason === 'aborted' ? 'Claude 已中斷' : reason === 'error' || reason === 'refusal' ? 'Claude 出錯了' : 'Claude 回應完成'
  const head = `${folderName(cwd)} · ${fmtDuration(durationMs)}`
  const text = preview(answer)
  return { title, body: text ? `${head}\n${text}` : head }
}

export const register: Register = on => {
  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    // 子代理的每一輪也會觸發, 只通知主對話
    if (e.agentId) return result

    const { title, body } = toastText(e.reason, e.answer, e.durationMs, await $.session.cwd())
    // 不等通知跑完, 避免拖慢回應結束
    void $.process
      .run(['powershell', '-NoProfile', '-NonInteractive', '-Command', '-'], {
        stdin: TOAST_SCRIPT,
        env: { CC_TOAST_TITLE: title, CC_TOAST_BODY: body },
        timeoutMs: 15_000,
      })
      .catch(() => {})

    return result
  })
}
