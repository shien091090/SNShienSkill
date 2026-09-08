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

function Fail([string]$stage, [string]$message, $requestId = $null, $remoteUrls = @(), $files = @(), [int]$code = 1) {
  Emit @{ status = 'error'; stage = $stage; message = $message; request_id = $requestId; remote_urls = $remoteUrls; files = $files }
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
try { $result = Get-WithRetry $responseUrl } catch { Fail 'result' (Get-HttpError $_) $requestId }

# Walk the result object; collect fal "File"-like objects: has `url` plus one of content_type/file_name/file_size/width
function Find-FileObjects($node, [ref]$acc) {
  if ($null -eq $node) { return }
  if ($node -is [string]) { return }
  if ($node -is [System.Collections.IEnumerable]) { foreach ($n in $node) { Find-FileObjects $n $acc }; return }
  if ($node -is [System.Management.Automation.PSCustomObject]) {
    $props = @($node.PSObject.Properties.Name)
    $isFile = ($props -contains 'url') -and (($props -contains 'content_type') -or ($props -contains 'file_name') -or ($props -contains 'file_size') -or ($props -contains 'width'))
    if ($isFile -and "$($node.url)" -like 'http*') { $acc.Value.Add($node) | Out-Null; return }
    foreach ($p in $props) { Find-FileObjects $node.$p $acc }
  }
}

$found = New-Object System.Collections.ArrayList
Find-FileObjects $result ([ref]$found)

# de-duplicate by url (e.g. hunyuan returns model_glb and model_urls.glb pointing to the same file)
$seen = @{}
$files = @()
foreach ($f in $found) { if (-not $seen.ContainsKey($f.url)) { $seen[$f.url] = $true; $files += $f } }

$elapsed = [int]((Get-Date) - $script:StartTime).TotalSeconds
if ($files.Count -eq 0) {
  Emit @{ status = 'ok'; files = @(); remote_urls = @(); request_id = $requestId; elapsed_sec = $elapsed; note = 'no downloadable file objects found'; raw = $result }
  exit 0
}

function Get-ExtFor($fileObj) {
  try { $ext = [IO.Path]::GetExtension(([Uri]$fileObj.url).AbsolutePath) } catch { $ext = '' }
  if ($ext) { return $ext.ToLower() }
  switch ("$($fileObj.content_type)") {
    'image/jpeg'        { return '.jpg' }
    'image/png'         { return '.png' }
    'image/webp'        { return '.webp' }
    'video/mp4'         { return '.mp4' }
    'audio/mpeg'        { return '.mp3' }
    'audio/mp3'         { return '.mp3' }
    'audio/wav'         { return '.wav' }
    'audio/x-wav'       { return '.wav' }
    'model/gltf-binary' { return '.glb' }
    default             { return '.bin' }
  }
}

if ([string]::IsNullOrWhiteSpace($OutDir)) { $OutDir = Join-Path (Get-Location) 'fal_out' }
$dir = Join-Path $OutDir $Category
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'

$saved = @()
$remote = @()
$i = 0
foreach ($f in $files) {
  $i++
  $remote += "$($f.url)"
  $ext = Get-ExtFor $f
  if ($files.Count -gt 1) { $name = ('{0}_{1:d2}{2}' -f $stamp, $i, $ext) } else { $name = "$stamp$ext" }
  $dest = Join-Path $dir $name
  try {
    Invoke-WebRequest -Uri $f.url -OutFile $dest -UseBasicParsing
    $saved += $dest
    Write-Output "$(Elapsed) SAVED $dest"
  } catch {
    Fail 'download' (Get-HttpError $_) $requestId $remote $saved
  }
}

$elapsed = [int]((Get-Date) - $script:StartTime).TotalSeconds
Emit @{ status = 'ok'; files = $saved; remote_urls = $remote; request_id = $requestId; elapsed_sec = $elapsed }
exit 0
