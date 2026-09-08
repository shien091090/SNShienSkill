<#
.SYNOPSIS
  fal.ai queue runner: (upload) -> submit -> poll -> download.
  stdout: one English line per event; the LAST line is always a single-line JSON result.
  exit codes: 0 ok, 1 error, 2 FAL_KEY missing, 3 timeout
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Endpoint,
  [string]$PayloadFile,
  [string]$OutDir,
  [string]$Category = 'misc',
  [string]$InputFile,
  [switch]$UploadOnly,
  # resume mode: skip upload/payload/submit and poll an existing request (used after a timeout)
  [string]$StatusUrl,
  [string]$ResponseUrl,
  [string]$RequestId,
  [int]$PollIntervalSec = 3,
  [int]$HeartbeatSec = 15,
  [int]$TimeoutSec = 180
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$script:StartTime = Get-Date

function Elapsed {
  $s = [int]((Get-Date) - $script:StartTime).TotalSeconds
  return ('[{0:d2}:{1:d2}]' -f [int][math]::Floor($s / 60), ($s % 60))
}

function Emit($obj) {
  $obj | ConvertTo-Json -Compress -Depth 10 | Write-Output
}

function Get-HttpError($err) {
  $msg = $err.Exception.Message
  try {
    $resp = $err.Exception.Response
    if ($resp) {
      $sr = New-Object IO.StreamReader($resp.GetResponseStream())
      $bodyText = $sr.ReadToEnd()
      if ($bodyText) { $msg = "$msg :: $bodyText" }
    }
  } catch { }
  return $msg
}

function Fail([string]$stage, [string]$message, $requestId = $null, $remoteUrls = @(), [int]$code = 1) {
  Emit @{ status = 'error'; stage = $stage; message = $message; request_id = $requestId; remote_urls = $remoteUrls }
  exit $code
}

# ---- auth ----
$key = $env:FAL_KEY
if ([string]::IsNullOrWhiteSpace($key)) {
  Emit @{ status = 'error'; stage = 'auth'; message = 'FAL_KEY not set. In PowerShell run: [Environment]::SetEnvironmentVariable("FAL_KEY","<key>","User") then restart Claude Code.' }
  exit 2
}
$headers = @{ Authorization = "Key $key" }

# ---- helpers: payload / http ----
function Read-Payload([string]$Path) {
  if ([string]::IsNullOrWhiteSpace($Path)) { Fail 'payload' '-PayloadFile is required (path to UTF-8 JSON).' }
  if (-not (Test-Path -LiteralPath $Path)) { Fail 'payload' "Payload file not found: $Path" }
  $json = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
  try { $null = $json | ConvertFrom-Json } catch { Fail 'payload' "Payload is not valid JSON: $($_.Exception.Message)" }
  return $json
}

function Submit-Job([string]$Ep, [string]$Json) {
  $bytes = [Text.Encoding]::UTF8.GetBytes($Json)
  try {
    return Invoke-RestMethod -Method Post -Uri "https://queue.fal.run/$Ep" -Headers $headers -ContentType 'application/json; charset=utf-8' -Body $bytes
  } catch { Fail 'submit' (Get-HttpError $_) }
}

function Get-WithRetry([string]$Uri) {
  for ($i = 1; $i -le 3; $i++) {
    try { return Invoke-RestMethod -Method Get -Uri $Uri -Headers $headers }
    catch { if ($i -eq 3) { throw }; Start-Sleep -Seconds 2 }
  }
}

# ---- MAIN ----
$resume = -not [string]::IsNullOrWhiteSpace($StatusUrl)
if ($resume) {
  if ([string]::IsNullOrWhiteSpace($ResponseUrl)) { Fail 'resume' '-ResponseUrl is required with -StatusUrl' }
  $requestId = $RequestId
  $statusUrl = $StatusUrl
  $responseUrl = $ResponseUrl
  $cancelUrl = $null
  Write-Output "$(Elapsed) RESUMED request_id=$requestId"
} else {
  $payload = Read-Payload $PayloadFile

  $submit = Submit-Job $Endpoint $payload
  $requestId = $submit.request_id
  $statusUrl = $submit.status_url
  $responseUrl = $submit.response_url
  $cancelUrl = $submit.cancel_url
  if (-not $requestId) { Fail 'submit' "No request_id in response: $($submit | ConvertTo-Json -Compress)" }
  Write-Output "$(Elapsed) SUBMITTED request_id=$requestId"
}

$lastLine = ''
$lastPrint = Get-Date
$st = $null
while ($true) {
  if (((Get-Date) - $script:StartTime).TotalSeconds -gt $TimeoutSec) {
    Emit @{ status = 'timeout'; request_id = $requestId; status_url = $statusUrl; response_url = $responseUrl; cancel_url = $cancelUrl }
    exit 3
  }
  try { $st = Get-WithRetry $statusUrl } catch { Fail 'poll' (Get-HttpError $_) $requestId }
  $line = "$($st.status)"
  if ($st.status -eq 'IN_QUEUE' -and $null -ne $st.queue_position) { $line += " position=$($st.queue_position)" }
  $changed = ($line -ne $lastLine)
  if ($changed -or ((Get-Date) - $lastPrint).TotalSeconds -ge $HeartbeatSec) {
    Write-Output "$(Elapsed) $line"
    $lastPrint = Get-Date
    $lastLine = $line
  }
  if ($st.status -eq 'COMPLETED') { break }
  Start-Sleep -Seconds $PollIntervalSec
}

# ---- RESULT ----
Emit @{ status = 'ok'; request_id = $requestId; message = 'poll done (download not implemented yet)' }
exit 0
