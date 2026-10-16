// 回應完成時的 Windows 系統通知: 標題是 session 名稱, 內文是這輪處理的內容
// 同一個 session 共用一個標記, 新通知取代舊的, 不會越疊越多

// 用 PowerShell 呼叫 Windows 通知; 文字走環境變數, 避免引號跳脫問題
export const TOAST_SCRIPT = `
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$texts = $xml.GetElementsByTagName('text')
$texts.Item(0).AppendChild($xml.CreateTextNode($env:CC_TOAST_TITLE)) > $null
$texts.Item(1).AppendChild($xml.CreateTextNode($env:CC_TOAST_BODY)) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
if ($env:CC_TOAST_TAG) {
  $toast.Tag = $env:CC_TOAST_TAG
  $toast.Group = 'claude-code'
}
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
`

// 內文最多約兩行, 超過交給 Windows 自動截斷
const BODY_CHARS = 90
// Windows 通知的標記上限 64 字元
export const TAG_CHARS = 64

// 回覆裡有字的段落接成一段, 去掉 markdown 符號與多餘空白
export function taskSummary(answer: string): string {
  const text = answer
    .split('\n')
    .map(l => l.replace(/^\s*([-*+]|\d+\.)\s+/, '').replace(/[#*`>_|]/g, '').trim())
    .filter(l => l.length > 0)
    .join(' ')
    .replace(/\s+/g, ' ')
  return text.length > BODY_CHARS ? text.slice(0, BODY_CHARS - 1) + '…' : text
}

export function folderName(cwd: string): string {
  return cwd.split(/[\\/]/).filter(Boolean).pop() ?? cwd
}

export function toastText(
  sessionTitle: string,
  cwd: string,
  reason: string,
  answer: string,
): { title: string; body: string } {
  const title = sessionTitle || `未命名 · ${folderName(cwd)}`
  const summary = taskSummary(answer)
  const status = reason === 'aborted' ? '已中斷' : reason === 'error' || reason === 'refusal' ? '出錯了' : ''
  const body = status ? (summary ? `${status}: ${summary}` : status) : summary || '回應完成'
  return { title, body }
}
