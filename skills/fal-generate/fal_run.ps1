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

# ---- MAIN ----
Emit @{ status = 'ok'; message = 'skeleton' }
exit 0
