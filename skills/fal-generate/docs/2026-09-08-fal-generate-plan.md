# fal-generate Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `fal-generate` Claude Code skill：使用者以自然語言在對話中生成圖片／影片／音樂／音效／語音／3D，經兩道確認（類別模式、費用）後呼叫 fal.ai Queue API，即時回報進度，產出存到本地。

**Architecture:** SKILL.md 是給 Claude 讀的操作手冊，負責意圖判斷、確認卡、費用估算、config 讀寫；`fal_run.ps1` 是無狀態的 PowerShell 5.1 腳本，負責上傳→送出→輪詢→下載，stdout 每行即一個 Monitor 事件、最後一行為 JSON 結果；`config.json` 持久化模型分級與使用者設定；`reference/` 存驗證過的端點表與 config 範本。

**Tech Stack:** Windows PowerShell 5.1（`Invoke-RestMethod` / `Invoke-WebRequest`）、fal.ai Queue REST API（`queue.fal.run`）、fal Storage API（`rest.fal.ai`）、fal Platform API（`api.fal.ai/v1/account/billing`）、Claude Code 工具：AskUserQuestion、Monitor、Write、Read、WebFetch。

**Spec:** `C:\Users\user\.claude\skills\fal-generate\docs\2026-09-08-fal-generate-design.md`

## Global Constraints

- 目標目錄 `C:\Users\user\.claude\skills\fal-generate\`；**非 git repo**，計畫中「Commit」步驟一律改為「確認檔案已存在且內容正確」
- PowerShell 5.1：無 `&&`/`||`/`?:`/`??`；`ConvertFrom-Json` 回傳 PSCustomObject；寫檔用 `-Encoding UTF8`
- 腳本 stdout 一律英文；最後一行必為單行 JSON（`status` ∈ `ok|error|timeout`）
- 退出碼：0 成功、1 錯誤、2 缺 `FAL_KEY`、3 逾時
- API Key 只從環境變數 `FAL_KEY` 讀取，任何檔案不得寫入 key
- 測試呼叫一律用最便宜端點 `fal-ai/flux/schnell`（約 $0.003/張）；會扣費的測試步驤需先告知使用者
- 端點 ID、輸入欄位名、輸出 URL 路徑一律以 OpenAPI 驗證結果為準（見 Task 1 表）
- 存檔規則：`{save_root}\{category}\{yyyyMMdd_HHmmss}.{ext}`，多檔 `_01`、`_02`

---

## 已驗證資料（2026-09-08，供各 Task 直接引用）

OpenAPI 查詢 URL 格式（有效端點回 200 JSON，無效回 404）：
`https://fal.ai/api/openapi/queue/openapi.json?endpoint_id={endpoint}`

| 類別 | 等級 | 端點 ID | Required | 輸入檔欄位 | 關鍵可選參數 | 輸出 URL 路徑 |
|---|---|---|---|---|---|---|
| image | high | `fal-ai/nano-banana-pro` | prompt | — | num_images(1-4), resolution 1K/2K/4K, aspect_ratio | `images[].url` |
| image | high/edit | `fal-ai/nano-banana-pro/edit` | prompt, image_urls | `image_urls`(array) | num_images | `images[].url` |
| image | medium | `fal-ai/nano-banana-2` | prompt | — | num_images(1-4), resolution 0.5K/1K/2K/4K, aspect_ratio | `images[].url` |
| image | medium/edit | `fal-ai/nano-banana-2/edit` | prompt | `image_urls`(array) | num_images | `images[].url` |
| image | low | `fal-ai/flux/schnell` | prompt | — | num_images, image_size(預設 landscape_4_3), output_format | `images[].url` |
| video | high | `bytedance/seedance-2.0/text-to-video` | prompt | — | duration "auto"/"4"–"15", resolution 480p/720p/1080p/4k | `video.url` |
| video | high/i2v | `bytedance/seedance-2.0/image-to-video` | prompt, image_url | `image_url` | duration 同上 | `video.url` |
| video | medium | `fal-ai/kling-video/v2.5-turbo/pro/text-to-video` | prompt | — | duration "5"/"10", aspect_ratio 16:9/9:16/1:1 | `video.url` |
| video | medium/i2v | `fal-ai/kling-video/v2.5-turbo/pro/image-to-video` | prompt, image_url | `image_url` | duration "5"/"10" | `video.url` |
| video | low | `fal-ai/bytedance/seedance/v1/lite/text-to-video` | prompt | — | duration "2"–"12", resolution 480p/720p/1080p | `video.url` |
| video | low/i2v | `fal-ai/bytedance/seedance/v1/lite/image-to-video` | prompt, image_url | `image_url` | duration "2"–"12" | `video.url` |
| music | high | `fal-ai/elevenlabs/music` | prompt | — | music_length_ms 3000–600000 | `audio.url` |
| music | medium | `fal-ai/minimax-music/v2.6` | prompt | — | lyrics, is_instrumental | `audio.url` |
| music | low | `fal-ai/minimax-music/v1.5` | prompt, lyrics_prompt | — | — | `audio.url` |
| sfx | single | `fal-ai/elevenlabs/sound-effects/v2` | text | — | duration_seconds 0.5–22 | `audio.url` |
| speech | high | `fal-ai/minimax/speech-2.8-hd` | prompt | — | voice_id(預設 Wise_Woman), language_boost(auto) | `audio.url` |
| speech | medium | `fal-ai/elevenlabs/tts/turbo-v2.5` | text | — | voice(預設 Rachel), language_code("zh") | `audio.url` |
| speech | low | `fal-ai/chatterbox/text-to-speech/multilingual` | text(≤300 字) | — | voice = 語言名，中文用 "chinese" | `audio.url` |
| 3d | high | `fal-ai/hunyuan-3d/v3.1/pro/image-to-3d` | input_image_url | `input_image_url` | — | `model_glb.url` |
| 3d | high/t23d | `fal-ai/hunyuan-3d/v3.1/pro/text-to-3d` | prompt | — | — | `model_glb.url` |
| 3d | medium | `fal-ai/trellis-2` | image_url | `image_url` | resolution 512/1024/1536 | `model_glb.url` |
| 3d | low | `fal-ai/trellis` | image_url | `image_url` | — | `model_mesh.url` |

其他已驗證 API：

- 送出：`POST https://queue.fal.run/{endpoint}`，header `Authorization: Key $FAL_KEY`，回 `{request_id, status_url, response_url, cancel_url}`
- 狀態：`GET {status_url}` 回 `{status: IN_QUEUE|IN_PROGRESS|COMPLETED, queue_position?}`
- 結果：`GET {response_url}`；取消：`PUT {cancel_url}`
- 上傳：`POST https://rest.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3`，body `{content_type, file_name}`，回 `{upload_url, file_url}`；再 `PUT {upload_url}`（**不帶 Authorization**）body 為檔案 bytes
- 餘額：`GET https://api.fal.ai/v1/account/billing?expand=credits`（需 ADMIN key）回 `{username, credits:{current_balance, currency}}`
- 模型頁定價文字：`https://fal.ai/models/{endpoint}` 頁面含 `Your request will cost $X per Y`

---

### Task 0: 前置條件——設定 ADMIN scope 的 FAL_KEY

**Files:** 無（環境變數）

**Interfaces:**
- Produces: 使用者層級環境變數 `FAL_KEY`，後續所有 Task 的腳本與測試都依賴

- [ ] **Step 1: 請使用者建立 key**

告知使用者：到 https://fal.ai/dashboard/keys → Create Key → scope 選 **ADMIN**（餘額查詢需要；ADMIN 包含 API 權限，一把即可）→ 立即複製（只顯示一次）。

- [ ] **Step 2: 請使用者在 PowerShell 設定使用者層級變數**

請使用者以 `!` 前綴在對話框自行執行（key 不經過 Claude）：

```powershell
[Environment]::SetEnvironmentVariable('FAL_KEY', '<貼上 key>', 'User')
```

之後**重啟 Claude Code**（新 process 才讀得到）。

- [ ] **Step 3: 驗證變數存在（不印出值）**

```powershell
if ([string]::IsNullOrWhiteSpace($env:FAL_KEY)) { 'FAL_KEY missing' } else { 'FAL_KEY present, length=' + $env:FAL_KEY.Length }
```

Expected: `FAL_KEY present, length=...`

- [ ] **Step 4: 驗證 ADMIN 權限（餘額 API）**

```powershell
$r = Invoke-RestMethod -Uri 'https://api.fal.ai/v1/account/billing?expand=credits' -Headers @{ Authorization = "Key $env:FAL_KEY" }
'balance=' + $r.credits.current_balance + ' ' + $r.credits.currency
```

Expected: `balance=<數字> USD`。若 401/403 → key 非 ADMIN scope，回到 Step 1 重建。

---

### Task 1: reference/default-models.md 與端點驗證腳本

**Files:**
- Create: `C:\Users\user\.claude\skills\fal-generate\reference\default-models.md`
- Create: `C:\Users\user\.claude\skills\fal-generate\tests\verify_endpoints.ps1`

**Interfaces:**
- Produces: `default-models.md`——SKILL.md 組 payload 時查閱的唯一參考；`verify_endpoints.ps1`——任何人可重跑確認端點仍存在

- [ ] **Step 1: 寫驗證腳本**

```powershell
# tests/verify_endpoints.ps1 — 對所有預設端點抓 OpenAPI，全部 200 才算通過
$endpoints = @(
  'fal-ai/nano-banana-pro','fal-ai/nano-banana-pro/edit','fal-ai/nano-banana-2','fal-ai/nano-banana-2/edit','fal-ai/flux/schnell',
  'bytedance/seedance-2.0/text-to-video','bytedance/seedance-2.0/image-to-video',
  'fal-ai/kling-video/v2.5-turbo/pro/text-to-video','fal-ai/kling-video/v2.5-turbo/pro/image-to-video',
  'fal-ai/bytedance/seedance/v1/lite/text-to-video','fal-ai/bytedance/seedance/v1/lite/image-to-video',
  'fal-ai/elevenlabs/music','fal-ai/minimax-music/v2.6','fal-ai/minimax-music/v1.5','fal-ai/elevenlabs/sound-effects/v2',
  'fal-ai/minimax/speech-2.8-hd','fal-ai/elevenlabs/tts/turbo-v2.5','fal-ai/chatterbox/text-to-speech/multilingual',
  'fal-ai/hunyuan-3d/v3.1/pro/image-to-3d','fal-ai/hunyuan-3d/v3.1/pro/text-to-3d','fal-ai/trellis-2','fal-ai/trellis'
)
$failed = @()
foreach ($e in $endpoints) {
  try {
    $r = Invoke-WebRequest -Uri "https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=$e" -UseBasicParsing -TimeoutSec 20
    $ok = ($r.StatusCode -eq 200) -and ($r.Content -match '"openapi"')
    if ($ok) { "OK   $e" } else { "FAIL $e (status $($r.StatusCode))"; $failed += $e }
  } catch { "FAIL $e ($($_.Exception.Message))"; $failed += $e }
}
if ($failed.Count -gt 0) { "FAILED: $($failed.Count)"; exit 1 } else { "ALL OK ($($endpoints.Count))"; exit 0 }
```

- [ ] **Step 2: 執行驗證**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\.claude\skills\fal-generate\tests\verify_endpoints.ps1"`
Expected: 22 行 `OK`，最後 `ALL OK (22)`，exit 0

- [ ] **Step 3: 確認各模型頁面定價**

對下列每個 URL 用 WebFetch，prompt 固定為「頁面上 "Your request will cost" 那句話的完整原文是什麼？只回那一句」，把結果填入 Step 4 表格的「價格」欄（覆蓋參考值）：

`https://fal.ai/models/fal-ai/nano-banana-pro`、`.../fal-ai/nano-banana-2`、`.../fal-ai/flux/schnell`、`.../bytedance/seedance-2.0/text-to-video`、`.../fal-ai/kling-video/v2.5-turbo/pro/text-to-video`、`.../fal-ai/bytedance/seedance/v1/lite/text-to-video`、`.../fal-ai/elevenlabs/music`、`.../fal-ai/minimax-music/v2.6`、`.../fal-ai/minimax-music/v1.5`、`.../fal-ai/elevenlabs/sound-effects/v2`、`.../fal-ai/minimax/speech-2.8-hd`、`.../fal-ai/elevenlabs/tts/turbo-v2.5`、`.../fal-ai/chatterbox/text-to-speech/multilingual`、`.../fal-ai/hunyuan-3d/v3.1/pro/image-to-3d`、`.../fal-ai/trellis-2`、`.../fal-ai/trellis`

抓不到的維持參考值並在表格標 `(約)`。

- [ ] **Step 4: 寫 reference/default-models.md**

```markdown
# fal-generate 預設模型表（驗證日期 2026-09-08）

價格單位：USD。`unit` 對應 config.json 的 `price.unit`。payload 範本中 `__INPUT_FILE_URL__` 由 fal_run.ps1 上傳後替換；`{prompt}` 等由 Claude 填入。

## image（張）

| tier | label | mode | endpoint | price | payload 範本 |
|---|---|---|---|---|---|
| high | Nano Banana Pro | generate | fal-ai/nano-banana-pro | 0.15/張（4K 0.30） | `{"prompt":"{prompt}","num_images":{n},"resolution":"1K"}` |
| high | Nano Banana Pro | edit | fal-ai/nano-banana-pro/edit | 0.15/張 | `{"prompt":"{prompt}","image_urls":["__INPUT_FILE_URL__"],"num_images":{n}}` |
| medium | Nano Banana 2 | generate | fal-ai/nano-banana-2 | 0.08/張 | `{"prompt":"{prompt}","num_images":{n},"resolution":"1K"}` |
| medium | Nano Banana 2 | edit | fal-ai/nano-banana-2/edit | 0.08/張 | `{"prompt":"{prompt}","image_urls":["__INPUT_FILE_URL__"],"num_images":{n}}` |
| low | FLUX Schnell | generate | fal-ai/flux/schnell | 0.003/張(約) | `{"prompt":"{prompt}","num_images":{n},"image_size":"landscape_4_3"}` |
| low | FLUX Schnell | edit | — | 不支援 → 依 §6.3 改用 medium | |

輸出：`images[].url`

## video（秒）

| tier | label | mode | endpoint | price | duration 可選值 | payload 範本 |
|---|---|---|---|---|---|---|
| high | Seedance 2.0 | text_to_video | bytedance/seedance-2.0/text-to-video | 0.30/秒(約, 720p) | "auto","4"–"15" | `{"prompt":"{prompt}","duration":"{sec}","resolution":"720p"}` |
| high | Seedance 2.0 | image_to_video | bytedance/seedance-2.0/image-to-video | 同上 | 同上 | `{"prompt":"{prompt}","image_url":"__INPUT_FILE_URL__","duration":"{sec}","resolution":"720p"}` |
| medium | Kling 2.5 Turbo Pro | text_to_video | fal-ai/kling-video/v2.5-turbo/pro/text-to-video | 0.07/秒 | "5","10" | `{"prompt":"{prompt}","duration":"{sec}","aspect_ratio":"16:9"}` |
| medium | Kling 2.5 Turbo Pro | image_to_video | fal-ai/kling-video/v2.5-turbo/pro/image-to-video | 0.07/秒 | "5","10" | `{"prompt":"{prompt}","image_url":"__INPUT_FILE_URL__","duration":"{sec}"}` |
| low | Seedance 1.0 Lite | text_to_video | fal-ai/bytedance/seedance/v1/lite/text-to-video | 0.036/秒(約, 720p) | "2"–"12" | `{"prompt":"{prompt}","duration":"{sec}","resolution":"720p"}` |
| low | Seedance 1.0 Lite | image_to_video | fal-ai/bytedance/seedance/v1/lite/image-to-video | 同上 | "2"–"12" | `{"prompt":"{prompt}","image_url":"__INPUT_FILE_URL__","duration":"{sec}","resolution":"720p"}` |

輸出：`video.url`。使用者要的秒數不在可選值內時，取最接近的較大值並在確認卡註明。

## music

| tier | label | endpoint | price | unit | payload 範本 |
|---|---|---|---|---|---|
| high | ElevenLabs Music | fal-ai/elevenlabs/music | 0.60/分（無條件進位） | 分 | `{"prompt":"{prompt}","music_length_ms":{ms}}` |
| medium | MiniMax Music 2.6 | fal-ai/minimax-music/v2.6 | 0.15/首 | 首 | 有歌詞 `{"prompt":"{style}","lyrics":"{lyrics}"}`；純音樂 `{"prompt":"{style}","is_instrumental":true}` |
| low | MiniMax Music 1.5 | fal-ai/minimax-music/v1.5 | 0.03/首 | 首 | `{"prompt":"{style}","lyrics_prompt":"{lyrics}"}`（**lyrics_prompt 必填**；使用者沒給歌詞時由 Claude 代寫 4–8 行並在確認卡顯示） |

輸出：`audio.url`

## sfx（不分級）

| endpoint | price | unit | payload 範本 |
|---|---|---|---|
| fal-ai/elevenlabs/sound-effects/v2 | 0.002/秒 | 秒 | `{"text":"{prompt}","duration_seconds":{sec}}`（0.5–22，預設 5） |

輸出：`audio.url`

## speech（千字）

| tier | label | endpoint | price | payload 範本 |
|---|---|---|---|---|
| high | MiniMax Speech-2.8 HD | fal-ai/minimax/speech-2.8-hd | 0.10/千字 | `{"prompt":"{text}","voice_id":"Wise_Woman","language_boost":"auto"}` |
| medium | ElevenLabs Turbo v2.5 | fal-ai/elevenlabs/tts/turbo-v2.5 | 0.05/千字 | `{"text":"{text}","voice":"Rachel","language_code":"zh"}` |
| low | Chatterbox Multilingual | fal-ai/chatterbox/text-to-speech/multilingual | 0.025/千字 | `{"text":"{text}","voice":"chinese"}`（text ≤ 300 字，超過需分段） |

輸出：`audio.url`

## 3d（次）

| tier | label | mode | endpoint | price | payload 範本 |
|---|---|---|---|---|---|
| high | Hunyuan 3D Pro v3.1 | image_to_3d | fal-ai/hunyuan-3d/v3.1/pro/image-to-3d | 0.375/次（PBR +0.15） | `{"input_image_url":"__INPUT_FILE_URL__"}` |
| high | Hunyuan 3D Pro v3.1 | text_to_3d | fal-ai/hunyuan-3d/v3.1/pro/text-to-3d | 0.375/次 | `{"prompt":"{prompt}"}` |
| medium | Trellis 2 | image_to_3d | fal-ai/trellis-2 | 0.30/次（1024） | `{"image_url":"__INPUT_FILE_URL__","resolution":1024}` |
| medium | Trellis 2 | text_to_3d | — | 不支援 → 先生圖再轉 3D（§6.3） | |
| low | Trellis | image_to_3d | fal-ai/trellis | 0.02/次 | `{"image_url":"__INPUT_FILE_URL__"}` |
| low | Trellis | text_to_3d | — | 不支援 → 先生圖再轉 3D | |

輸出：Hunyuan / Trellis 2 → `model_glb.url`；Trellis → `model_mesh.url`

## 其他 API

- 餘額：`GET https://api.fal.ai/v1/account/billing?expand=credits` → `credits.current_balance`
- OpenAPI：`https://fal.ai/api/openapi/queue/openapi.json?endpoint_id={endpoint}`
- 模型頁定價：`https://fal.ai/models/{endpoint}` 內 `Your request will cost $X per Y`
- 重新驗證端點：`tests/verify_endpoints.ps1`
```

- [ ] **Step 5: 確認檔案**

Run: `Test-Path "C:\Users\user\.claude\skills\fal-generate\reference\default-models.md"`
Expected: `True`；表格中所有端點 ID 與 Step 2 腳本清單一致（22 個）。

---

### Task 2: fal_run.ps1 骨架——參數、金鑰檢查、輸出協定

**Files:**
- Create: `C:\Users\user\.claude\skills\fal-generate\fal_run.ps1`

**Interfaces:**
- Produces: 參數 `-Endpoint -PayloadFile -OutDir -Category -InputFile -UploadOnly -StatusUrl -ResponseUrl -RequestId -PollIntervalSec -HeartbeatSec -TimeoutSec`；函式 `Elapsed`、`Emit`、`Fail`、`Get-HttpError`；變數 `$headers`、`$script:StartTime`。Task 3–5 在此檔案的 `# ---- MAIN ----` 區塊之後追加

- [ ] **Step 1: 寫骨架**

```powershell
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
```

- [ ] **Step 2: 測試缺少 FAL_KEY 的路徴**

Run:
```powershell
$saved = $env:FAL_KEY; $env:FAL_KEY = ''
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\.claude\skills\fal-generate\fal_run.ps1" -Endpoint x
"exit=$LASTEXITCODE"
$env:FAL_KEY = $saved
```
Expected: 一行 JSON 含 `"stage":"auth"`，然後 `exit=2`

- [ ] **Step 3: 測試有 FAL_KEY 時走到 MAIN**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\.claude\skills\fal-generate\fal_run.ps1" -Endpoint x; "exit=$LASTEXITCODE"`
Expected: `{"status":"ok","message":"skeleton"}`，`exit=0`

---

### Task 3: fal_run.ps1 送出、輪詢、逾時

**Files:**
- Modify: `C:\Users\user\.claude\skills\fal-generate\fal_run.ps1`（取代 `# ---- MAIN ----` 之後的內容）

**Interfaces:**
- Consumes: Task 2 的 `$headers`、`Emit`、`Fail`、`Get-HttpError`、`Elapsed`
- Produces: 函式 `Read-Payload`、`Submit-Job`、`Get-WithRetry`；變數 `$requestId`、`$responseUrl`、`$cancelUrl`；輪詢結束時 `$st.status -eq 'COMPLETED'`。Task 4 接在 `# ---- RESULT ----` 之後

- [ ] **Step 1: 以下取代 `# ---- MAIN ----` 起的內容**

```powershell
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
```

- [ ] **Step 2: 準備測試 payload**

Write `C:\Users\user\AppData\Local\Temp\claude\C--Users-user\e3f76612-e5ca-4283-991e-31c62f04572c\scratchpad\payload_schnell.json`：
```json
{"prompt":"a cute corgi puppy sitting on grass, photo","num_images":1,"image_size":"square"}
```

- [ ] **Step 3: 測試錯誤端點（不扣費）**

Run:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\.claude\skills\fal-generate\fal_run.ps1" -Endpoint 'fal-ai/this-model-does-not-exist' -PayloadFile "C:\Users\user\AppData\Local\Temp\claude\C--Users-user\e3f76612-e5ca-4283-991e-31c62f04572c\scratchpad\payload_schnell.json"; "exit=$LASTEXITCODE"
```
Expected: JSON `"stage":"submit"`，message 含 404 或 Not Found，`exit=1`

- [ ] **Step 4: 測試缺 PayloadFile**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File "...\fal_run.ps1" -Endpoint 'fal-ai/flux/schnell'; "exit=$LASTEXITCODE"`
Expected: `"stage":"payload"`，`exit=1`

- [ ] **Step 5: 測試逾時路徑（會送出一張 schnell，約 $0.003，先告知使用者）**

Run: 同 Step 3 但 `-Endpoint 'fal-ai/flux/schnell' -TimeoutSec 0`
Expected: 先一行 `[00:0x] SUBMITTED request_id=...`，再一行 JSON `"status":"timeout"` 含 `cancel_url`，`exit=3`

- [ ] **Step 6: 測試正常輪詢到 COMPLETED（約 $0.003）**

Run: 同上但 `-TimeoutSec 120`
Expected: `SUBMITTED` → 若干 `IN_QUEUE`/`IN_PROGRESS` 行（狀態變才印，或每 15 秒一行）→ `COMPLETED` → JSON `"status":"ok"`，`exit=0`

- [ ] **Step 7: 測試續接模式（不扣費，重用 Step 5 逾時輸出的 URL）**

取 Step 5 JSON 中的 `status_url`、`response_url`、`request_id`：
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "...\fal_run.ps1" -Endpoint 'fal-ai/flux/schnell' -StatusUrl '<status_url>' -ResponseUrl '<response_url>' -RequestId '<request_id>' -TimeoutSec 60; "exit=$LASTEXITCODE"
```
Expected: 第一行 `RESUMED request_id=...`（沒有 SUBMITTED、沒有讀 PayloadFile）→ `COMPLETED`（該任務早已完成）→ JSON `"status":"ok"`，`exit=0`

---

### Task 4: fal_run.ps1 取結果、抽出檔案、下載命名

**Files:**
- Modify: `C:\Users\user\.claude\skills\fal-generate\fal_run.ps1`（取代 `# ---- RESULT ----` 之後）

**Interfaces:**
- Consumes: Task 3 的 `$responseUrl`、`$requestId`、`Get-WithRetry`
- Produces: 最後一行 JSON `{"status":"ok","files":[...絕對路徑],"remote_urls":[...],"request_id":"...","elapsed_sec":N}`；SKILL.md 讀 `files[0]` 更新 `last_output`

- [ ] **Step 1: 以下取代 `# ---- RESULT ----` 起的內容**

```powershell
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
    Fail 'download' (Get-HttpError $_) $requestId $remote
  }
}

$elapsed = [int]((Get-Date) - $script:StartTime).TotalSeconds
Emit @{ status = 'ok'; files = $saved; remote_urls = $remote; request_id = $requestId; elapsed_sec = $elapsed }
exit 0
```

- [ ] **Step 2: 全流程測試（約 $0.003）**

Run:
```powershell
$out = "C:\Users\user\AppData\Local\Temp\claude\C--Users-user\e3f76612-e5ca-4283-991e-31c62f04572c\scratchpad\fal_test_out"
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\.claude\skills\fal-generate\fal_run.ps1" -Endpoint 'fal-ai/flux/schnell' -PayloadFile "C:\Users\user\AppData\Local\Temp\claude\C--Users-user\e3f76612-e5ca-4283-991e-31c62f04572c\scratchpad\payload_schnell.json" -OutDir $out -Category image -TimeoutSec 120
"exit=$LASTEXITCODE"
Get-ChildItem "$out\image"
```
Expected: 事件行 → `SAVED ...\image\yyyyMMdd_HHmmss.jpg`（或 .jpeg/.png）→ JSON `"status":"ok"` 且 `files` 有 1 個路徑，`exit=0`；`Get-ChildItem` 列出該檔且大小 > 10KB

- [ ] **Step 3: 多檔命名測試（約 $0.006）**

把 payload 的 `num_images` 改 2 再跑 Step 2。
Expected: 兩個檔 `..._01.jpg`、`..._02.jpg`，JSON `files` 長度 2

- [ ] **Step 4: 用 Read 工具開啟其中一張圖確認是可辨識的圖片**

Expected: 看得到一隻柯基。

---

### Task 5: fal_run.ps1 輸入檔上傳（-InputFile / -UploadOnly）

**Files:**
- Modify: `C:\Users\user\.claude\skills\fal-generate\fal_run.ps1`（在 `# ---- MAIN ----` 的 `$payload = Read-Payload ...` 之後、`Submit-Job` 之前插入；並新增 `Upload-File` 函式於 helpers 區）

**Interfaces:**
- Consumes: `$headers`、`Fail`
- Produces: payload 中 `__INPUT_FILE_URL__` 被替換；`-UploadOnly` 時輸出 `{"status":"ok","file_url":"https://v3.fal.media/..."}`

- [ ] **Step 1: 在 `# ---- helpers: payload / http ----` 區塊加入**

```powershell
function Get-MimeFor([string]$Path) {
  switch ([IO.Path]::GetExtension($Path).ToLower()) {
    '.png'  { return 'image/png' }
    '.jpg'  { return 'image/jpeg' }
    '.jpeg' { return 'image/jpeg' }
    '.webp' { return 'image/webp' }
    '.gif'  { return 'image/gif' }
    '.mp4'  { return 'video/mp4' }
    '.mp3'  { return 'audio/mpeg' }
    '.wav'  { return 'audio/wav' }
    '.glb'  { return 'model/gltf-binary' }
    default { return 'application/octet-stream' }
  }
}

function Upload-File([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { Fail 'upload' "Input file not found: $Path" }
  $mime = Get-MimeFor $Path
  $body = @{ content_type = $mime; file_name = [IO.Path]::GetFileName($Path) } | ConvertTo-Json -Compress
  try {
    $init = Invoke-RestMethod -Method Post -Uri 'https://rest.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3' -Headers $headers -ContentType 'application/json' -Body $body
  } catch { Fail 'upload' ("initiate failed: " + (Get-HttpError $_)) }
  if (-not $init.upload_url -or -not $init.file_url) { Fail 'upload' "initiate returned no upload_url/file_url: $($init | ConvertTo-Json -Compress)" }
  try {
    # signed URL: do NOT send Authorization header
    Invoke-RestMethod -Method Put -Uri $init.upload_url -InFile $Path -ContentType $mime | Out-Null
  } catch { Fail 'upload' ("PUT failed: " + (Get-HttpError $_)) }
  Write-Output "$(Elapsed) UPLOADED $([IO.Path]::GetFileName($Path)) -> $($init.file_url)"
  return "$($init.file_url)"
}
```

- [ ] **Step 2: 在 MAIN 的 `$payload = Read-Payload $PayloadFile` 前後改為**

```powershell
（放在 `} else {` 分支內、原本 `$payload = Read-Payload $PayloadFile` 的位置；`-UploadOnly` 檢查放在 `$resume` 判斷之前）

```powershell
# ---- MAIN ----
if ($UploadOnly) {
  if ([string]::IsNullOrWhiteSpace($InputFile)) { Fail 'upload' '-UploadOnly requires -InputFile' }
  $u = Upload-File $InputFile
  Emit @{ status = 'ok'; file_url = $u }
  exit 0
}

$resume = -not [string]::IsNullOrWhiteSpace($StatusUrl)
if ($resume) {
  # ...（Task 3 的續接分支，不變）
} else {
  $fileUrl = $null
  if (-not [string]::IsNullOrWhiteSpace($InputFile)) { $fileUrl = Upload-File $InputFile }

  $payload = Read-Payload $PayloadFile
  if ($fileUrl) { $payload = $payload.Replace('__INPUT_FILE_URL__', $fileUrl) }
  if ($payload.Contains('__INPUT_FILE_URL__')) { Fail 'payload' 'Payload contains __INPUT_FILE_URL__ but no -InputFile was given.' }

  # ...（Task 3 的 Submit-Job 與後續，不變）
}
```

- [ ] **Step 3: 產生測試用 1x1 PNG**

```powershell
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap 8, 8
for ($x=0;$x -lt 8;$x++){for($y=0;$y -lt 8;$y++){$bmp.SetPixel($x,$y,[System.Drawing.Color]::Orange)}}
$p = "C:\Users\user\AppData\Local\Temp\claude\C--Users-user\e3f76612-e5ca-4283-991e-31c62f04572c\scratchpad\test_upload.png"
$bmp.Save($p, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose(); Get-Item $p | Select-Object Length
```
Expected: Length > 0

- [ ] **Step 4: 測試 -UploadOnly（免費）**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File "...\fal_run.ps1" -Endpoint x -InputFile "<上面的 png 路徑>" -UploadOnly; "exit=$LASTEXITCODE"`
Expected: `[..] UPLOADED test_upload.png -> https://v3.fal.media/...`，JSON `"file_url":"https://..."`，`exit=0`；用 WebFetch 或瀏覽器開 file_url 可看到橘色方塊

- [ ] **Step 5: 測試佔位字串未替換的保護**

Write payload `{"prompt":"x","image_urls":["__INPUT_FILE_URL__"]}` 為 `payload_edit.json`，執行 `-Endpoint 'fal-ai/nano-banana-2/edit' -PayloadFile payload_edit.json`（不給 -InputFile）
Expected: `"stage":"payload"` 含 `no -InputFile`，`exit=1`，**未送出任何請求**

- [ ] **Step 6: 回歸 Task 4 Step 2**

重跑 Task 4 Step 2 確認無 -InputFile 的一般流程仍正常。

---

### Task 6: reference/config.template.json

**Files:**
- Create: `C:\Users\user\.claude\skills\fal-generate\reference\config.template.json`

**Interfaces:**
- Produces: 初始化時 SKILL.md 讀此範本、填入 `save_root`、`low_balance_threshold` 後寫成 `config.json`。所有 tier 的 `endpoints` 鍵名（`generate`/`edit`/`text_to_video`/`image_to_video`/`text_to_3d`/`image_to_3d`）與 `default-models.md` 的 mode 欄一致

- [ ] **Step 1: 寫範本（價格填 Task 1 Step 3 確認後的值）**

```json
{
  "version": 1,
  "save_root": null,
  "low_balance_threshold": null,
  "poll_interval_sec": 3,
  "heartbeat_sec": 15,
  "timeout_sec": { "image": 180, "music": 180, "sfx": 180, "speech": 180, "video": 600, "3d": 600 },
  "last_output": { "image": null, "video": null, "music": null, "sfx": null, "speech": null, "3d": null },
  "schema_cache": {},
  "categories": {
    "image": {
      "current": "medium",
      "tiers": {
        "high":   { "label": "Nano Banana Pro", "endpoints": { "generate": "fal-ai/nano-banana-pro", "edit": "fal-ai/nano-banana-pro/edit" }, "price": { "amount": 0.15, "unit": "張", "approx": false } },
        "medium": { "label": "Nano Banana 2",   "endpoints": { "generate": "fal-ai/nano-banana-2",   "edit": "fal-ai/nano-banana-2/edit" },   "price": { "amount": 0.08, "unit": "張", "approx": false } },
        "low":    { "label": "FLUX Schnell",    "endpoints": { "generate": "fal-ai/flux/schnell",    "edit": null },                          "price": { "amount": 0.003, "unit": "張", "approx": true } }
      }
    },
    "video": {
      "current": "medium",
      "tiers": {
        "high":   { "label": "Seedance 2.0",        "endpoints": { "text_to_video": "bytedance/seedance-2.0/text-to-video",                 "image_to_video": "bytedance/seedance-2.0/image-to-video" },                 "price": { "amount": 0.30,  "unit": "秒", "approx": true } },
        "medium": { "label": "Kling 2.5 Turbo Pro", "endpoints": { "text_to_video": "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",     "image_to_video": "fal-ai/kling-video/v2.5-turbo/pro/image-to-video" },     "price": { "amount": 0.07,  "unit": "秒", "approx": false } },
        "low":    { "label": "Seedance 1.0 Lite",   "endpoints": { "text_to_video": "fal-ai/bytedance/seedance/v1/lite/text-to-video",     "image_to_video": "fal-ai/bytedance/seedance/v1/lite/image-to-video" },     "price": { "amount": 0.036, "unit": "秒", "approx": true } }
      }
    },
    "music": {
      "current": "medium",
      "tiers": {
        "high":   { "label": "ElevenLabs Music",  "endpoints": { "generate": "fal-ai/elevenlabs/music" },   "price": { "amount": 0.60, "unit": "分", "approx": false } },
        "medium": { "label": "MiniMax Music 2.6", "endpoints": { "generate": "fal-ai/minimax-music/v2.6" }, "price": { "amount": 0.15, "unit": "首", "approx": false } },
        "low":    { "label": "MiniMax Music 1.5", "endpoints": { "generate": "fal-ai/minimax-music/v1.5" }, "price": { "amount": 0.03, "unit": "首", "approx": false } }
      }
    },
    "sfx": {
      "single": { "label": "ElevenLabs SFX v2", "endpoints": { "generate": "fal-ai/elevenlabs/sound-effects/v2" }, "price": { "amount": 0.002, "unit": "秒", "approx": false } }
    },
    "speech": {
      "current": "medium",
      "tiers": {
        "high":   { "label": "MiniMax Speech-2.8 HD",    "endpoints": { "generate": "fal-ai/minimax/speech-2.8-hd" },                  "price": { "amount": 0.10,  "unit": "千字", "approx": false } },
        "medium": { "label": "ElevenLabs Turbo v2.5",    "endpoints": { "generate": "fal-ai/elevenlabs/tts/turbo-v2.5" },              "price": { "amount": 0.05,  "unit": "千字", "approx": false } },
        "low":    { "label": "Chatterbox Multilingual",  "endpoints": { "generate": "fal-ai/chatterbox/text-to-speech/multilingual" }, "price": { "amount": 0.025, "unit": "千字", "approx": false } }
      }
    },
    "3d": {
      "current": "medium",
      "tiers": {
        "high":   { "label": "Hunyuan 3D Pro v3.1", "endpoints": { "image_to_3d": "fal-ai/hunyuan-3d/v3.1/pro/image-to-3d", "text_to_3d": "fal-ai/hunyuan-3d/v3.1/pro/text-to-3d" }, "price": { "amount": 0.375, "unit": "次", "approx": false } },
        "medium": { "label": "Trellis 2",           "endpoints": { "image_to_3d": "fal-ai/trellis-2",                       "text_to_3d": null },                                     "price": { "amount": 0.30,  "unit": "次", "approx": false } },
        "low":    { "label": "Trellis",             "endpoints": { "image_to_3d": "fal-ai/trellis",                         "text_to_3d": null },                                     "price": { "amount": 0.02,  "unit": "次", "approx": false } }
      }
    }
  }
}
```

- [ ] **Step 2: 驗證 JSON 可解析且結構完整**

```powershell
$c = Get-Content "C:\Users\user\.claude\skills\fal-generate\reference\config.template.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$cats = @($c.categories.PSObject.Properties.Name)
"categories=$($cats -join ',')"
foreach ($k in $cats) { if ($k -eq 'sfx') { "sfx single=$($c.categories.sfx.single.endpoints.generate)" } else { "$k current=$($c.categories.$k.current) tiers=$(@($c.categories.$k.tiers.PSObject.Properties.Name) -join ',')" } }
```
Expected: `categories=image,video,music,sfx,speech,3d`；五個類別 `current=medium tiers=high,medium,low`；sfx 一行

- [ ] **Step 3: 交叉比對**

範本內每個非 null 端點 ID 都出現在 `tests/verify_endpoints.ps1` 清單中（22 個）。用 Grep 逐一確認或目視比對。

---

### Task 7: SKILL.md 操作手冊

**Files:**
- Create: `C:\Users\user\.claude\skills\fal-generate\SKILL.md`

**Interfaces:**
- Consumes: `fal_run.ps1` 介面（Task 2–5）、`reference/default-models.md`（Task 1）、`reference/config.template.json`（Task 6）
- Produces: Claude 可依此執行完整流程

- [ ] **Step 1: 寫 SKILL.md**

````markdown
---
name: fal-generate
description: 透過 fal.ai 生成圖片／影片／音樂／音效／語音／3D。當使用者說「幫我生成／生一張／畫一個／做一段影片／配個音／唸一段／做個 3D 模型／把剛剛那張改成…」等任何生成媒體的意圖時使用，即使沒提到 fal。也負責「切成貴的／便宜的／切換到 XXX 模型／更新價格表」等設定指令。
---

# fal-generate

skill 目錄：`~/.claude/skills/fal-generate/`（下稱 `$SKILL`）。設定檔 `$SKILL/config.json`；範本 `$SKILL/reference/config.template.json`；模型表 `$SKILL/reference/default-models.md`；腳本 `$SKILL/fal_run.ps1`。
所有 payload 檔寫到 scratchpad 目錄，不寫進 `$SKILL`。

## 0. 每次觸發的固定順序

1. 讀 `$SKILL/config.json`；不存在 → 執行 §1 初始化後再繼續
2. 若訊息是**設定指令**（§5）→ 執行後結束，除非同句還有生成指令
3. 判斷類別與模式（§2）→ Gate 0 確認卡
4. 查餘額、決定等級與端點、估算費用（§3、§4）→ Gate 1 確認卡
5. 寫 payload 檔 → 以 Monitor 執行 `fal_run.ps1`（§6）→ 逐事件回報
6. 收尾：更新 `last_output`、回報結果（§7）

## 1. 初始化（config.json 不存在時，只跑一次）

1. 用 AskUserQuestion 問「生成的檔案要存到哪個資料夾？」（建議 `D:\FalOutputs`），使用者可用「Other」輸入路徑
2. 用 AskUserQuestion 問「餘額低於多少美金時自動改用便宜方案？」選項：`$5（推薦）` / `$10` / `$20`
3. 讀 `config.template.json`，填入 `save_root`、`low_balance_threshold`，用 Write 寫成 `$SKILL/config.json`（UTF-8）
4. 告知：「已初始化 fal-generate。所有類別預設使用【適中】方案；說『切成貴的／便宜的』可切換。」

## 2. 類別與模式判斷（Gate 0）

| 使用者說法線索 | 類別 |
|---|---|
| 圖、圖片、畫、插圖、海報、照片 | `image` |
| 影片、動畫、短片、動起來 | `video` |
| 音樂、背景樂、BGM、一首歌、配樂 | `music` |
| 音效、聲音效果、sound effect、爆炸聲 | `sfx` |
| 唸、朗讀、語音、配音、TTS、旁白 | `speech` |
| 3D、模型、立體 | `3d` |

模式：

- 提到既有檔案（本機路徑、「剛剛那張／上一張／這張」）→ image `edit`、video `image_to_video`、3d `image_to_3d`
- 「剛剛那張／上一張」→ 用 `config.last_output.image`（影片/3D 亦可引用 image 的 last_output 作為輸入圖）；為 null 時問路徑
- 否則 → image `generate`、video `text_to_video`、3d `text_to_3d`、music/sfx/speech `generate`

Gate 0 卡片（AskUserQuestion，單選）：

> 問題：「要用 fal 生成【{類別中文} · {模式中文}】嗎？{有輸入檔時：底圖：`{路徑}`}」
> 選項：`對，繼續` / `不對，換類別或模式` / `取消`

類別判斷不出 → 卡片改列六個類別讓使用者選。選「換類別或模式」→ 再問一次列出類別與模式。選「取消」→ 結束，不呼叫任何 API。

## 3. 等級、端點、餘額

### 3.1 決定等級

`tier = config.categories[類別].current`（sfx 沒有等級，直接用 `single`）。同句含切換指令則先依 §5 切換並寫回 config。

### 3.2 查餘額與低額度降級

```powershell
$r = Invoke-RestMethod -Uri 'https://api.fal.ai/v1/account/billing?expand=credits' -Headers @{ Authorization = "Key $env:FAL_KEY" }
$r.credits.current_balance
```

- 成功且 `balance < low_balance_threshold`：
  - 若 tier ≠ low → 本次改用 `low`，並將 `config.categories[類別].current = "low"` 寫回
  - 不論 tier 為何，Gate 1 卡片加一行「⚠️ 額度剩 ${balance}，低於門檻 ${threshold}」（使用者手動切回較貴方案時，每次都會再看到這行）
- 失敗（401/403/網路）→ 卡片加一行「（餘額查詢失敗：{原因}，略過自動降級）」，繼續

### 3.3 決定端點

`endpoint = config.categories[類別].tiers[tier].endpoints[模式]`。

為 `null`（該等級不支援此模式）→ 依序往 `medium`、`high` 找第一個非 null 的端點，改用該等級**僅此一次**（不寫回 config），並在 Gate 1 卡片註明「{原等級} 不支援{模式}，本次改用 {替代等級} {label}」。

3d 的 `text_to_3d` 在 medium/low 皆為 null 時 → 兩段式：先以 `image` 類別目前等級的 `generate` 生一張參考圖（payload 加 `"aspect_ratio":"1:1"` 或 `image_size":"square"`），再以該圖走 `image_to_3d`。Gate 1 卡片分兩行列出兩段費用，總計後確認。第一段完成後不再另外確認，直接進第二段。

### 3.4 使用者指定任意模型（「切換到 XXX 模型」「用 XXX 生」）

1. 以 WebFetch 查 `https://fal.ai/models/{猜測的 endpoint}`；不確定 ID 時先 WebSearch `fal.ai models {名稱}` 取得正確 endpoint
2. 用 WebFetch 抓 `https://fal.ai/api/openapi/queue/openapi.json?endpoint_id={endpoint}`，取 required 欄位、輸入檔欄位名、輸出 URL 路徴，寫入 `config.schema_cache[endpoint]`（含 `fetched_at`）
3. 用 WebFetch 抓模型頁，找 `Your request will cost $X per Y`；抓不到 → Gate 1 卡片標「價格未知」，由使用者決定
4. 本次以此 endpoint 執行。完成後 AskUserQuestion「要把 {label} 存為【{類別}】的哪個等級？」選項：`高品質` / `適中` / `便宜` / `不存`，選了就覆寫該 tier 的 label/endpoints/price

## 4. 費用估算（Gate 1）

數量解析（沒說就用預設，**預設值要寫在卡片上**）：

| 類別 | 解析 | 預設 | 費用 |
|---|---|---|---|
| image | 「N 張」 | 1 | `amount × N` |
| video | 「N 秒」→ 對到端點 duration 可選值（取最接近的較大值） | 5 | `amount × 秒` |
| music（/分） | 「N 秒／N 分」→ `music_length_ms`；費用以分鐘無條件進位 | 60 秒 | `amount × ceil(秒/60)` |
| music（/首） | — | 1 | `amount` |
| sfx | 「N 秒」（0.5–22） | 5 | `amount × 秒` |
| speech | 文本字數（含標點） | — | `amount × ceil(字數/1000)`；Chatterbox 超過 300 字要分段，每段一次呼叫 |
| 3d | — | 1 | `amount`（Hunyuan 需 PBR 時 +0.15） |

Gate 1 卡片（AskUserQuestion，單選）：

> 問題：「【{類別} · {模式}】{等級中文}方案 {label}｜{數量說明，如 1 張 / 5 秒 / 1 首 / 128 字}｜預估 ${費用}{approx 時前綴「約」}｜餘額 ${balance}{警告行}{替代方案說明行}{兩段式費用明細}」
> 選項：`確認執行` / `換等級` / `取消`

「換等級」→ AskUserQuestion 列 `高品質 {label} ${price}` / `適中 …` / `便宜 …`，選後**只影響本次**（不寫回），重算費用再出一次 Gate 1。

## 5. 設定指令

| 說法 | 動作 |
|---|---|
| 切成貴的／高品質的（可帶類別，如「圖片切成貴的」；沒帶類別且同句有生成指令 → 用該類別；都沒有 → 問哪個類別） | `current = "high"` 寫回 |
| 切成便宜的／快的／不要求品質 | `current = "low"` |
| 切回適中／中等 | `current = "medium"` |
| 切換到 XXX 模型／用 XXX 生 | §3.4 |
| 更新價格表 | 對 config 內每個 endpoint 用 WebFetch 抓模型頁 `Your request will cost $X per Y`，更新 `price.amount`、`approx=false`；抓不到的保留並標 `approx=true`；最後列出變動清單 |
| 存到哪／改存檔位置 | 問新路徑，更新 `save_root` |
| 額度門檻改成 N | 更新 `low_balance_threshold` |

每次寫回 config：讀 → 修改 → Write 整份（UTF-8，保持 2 空格縮排）。

## 6. 執行

1. 依 `default-models.md` 的 payload 範本（或 `schema_cache`）組 JSON；prompt 若為中文，**翻成英文**再填入（多數模型英文效果較穩），但 speech 的文本與 music 歌詞保持原文
2. Write 到 `{scratchpad}/fal_payload_{yyyyMMddHHmmss}.json`（UTF-8）
3. 用 **Monitor** 執行（command 在 Bash 環境下執行，路徑用正斜線）：

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/Users/user/.claude/skills/fal-generate/fal_run.ps1" -Endpoint "{endpoint}" -PayloadFile "{payload 路徑}" -OutDir "{save_root}" -Category {類別} -PollIntervalSec {config.poll_interval_sec} -HeartbeatSec {config.heartbeat_sec} -TimeoutSec {config.timeout_sec[類別]} {有輸入檔時：-InputFile "{路徑}"} 2>&1
```

   - `description`：`fal {類別} {label}`
   - `timeout_ms`：`(timeout_sec[類別] + 30) * 1000`
   - `persistent: false`
4. 每個事件行翻成中文簡短回報：`SUBMITTED` → 「已送出，request_id …」；`IN_QUEUE position=N` → 「排隊中，前面還有 N 個」；`IN_PROGRESS` → 「生成中…（已 mm:ss）」；`UPLOADED` → 「輸入檔已上傳」；`SAVED` → 「已存檔 …」
5. 最後一行 JSON：
   - `status=ok` → §7
   - `status=error` → 依 `stage` 說明：`auth` 教設定 FAL_KEY；`submit` 顯示 message（常見：422 參數錯 → 檢查 payload；404 端點不存在 → 建議「更新價格表」或指定其他模型；403/402 餘額不足）；`poll`/`result` 顯示 message 與 request_id；`download` 列出 `remote_urls` 請使用者手動存。**不自動重試**，問「要換等級再試一次嗎？」
   - `status=timeout` → AskUserQuestion「已等待 {timeout_sec} 秒仍未完成（fal 端仍在執行、會照常計費）。」選項：`再等一輪` / `取消任務` / `先不管它`
     - 再等一輪 → 再跑一次 Monitor，改用**續接模式**（不會重新送出）：

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/Users/user/.claude/skills/fal-generate/fal_run.ps1" -Endpoint "{endpoint}" -StatusUrl "{status_url}" -ResponseUrl "{response_url}" -RequestId "{request_id}" -OutDir "{save_root}" -Category {類別} -TimeoutSec {config.timeout_sec[類別]} 2>&1
```

       結果處理與一般流程相同（最後一行 JSON）
     - 取消任務 → PowerShell：`Invoke-RestMethod -Method Put -Uri '{cancel_url}' -Headers @{ Authorization = "Key $env:FAL_KEY" }`；回報「已送出取消」；若拋 400 → 回報「任務已完成、無法取消」並改走續接模式把結果抓下來
     - 先不管它 → 回報 request_id 與 status_url，結束

## 7. 收尾

1. `config.last_output[類別] = files[0]`，寫回
2. 再查一次餘額（失敗就略過）
3. 回報：「完成 ✅ 已存到 `{files}`（{elapsed_sec} 秒）。預估花費 ${費用}，目前餘額 ${balance}。」
4. 圖片類：用 Read 工具開啟第一張讓使用者在對話中看到縮圖

## 8. 注意事項

- 絕不把 `FAL_KEY` 的值印到對話或寫入檔案
- 任何會扣費的呼叫都必須先經過 Gate 1 確認；兩段式 3D 只在第一段前確認一次（卡片已列兩段費用）
- 腳本 stdout 是英文，回報時翻中文；最後一行 JSON 才是結果，不要把中間事件行當結果
- 使用者只說「取消」而沒有進行中的任務 → 回覆目前沒有任務
````

- [ ] **Step 2: 對照 spec 逐節檢查**

用下列清單逐項在 SKILL.md 找到對應段落，缺一補一：spec §3.2 Gate 0 → SKILL §2；§3.3 初始化 → §1；§3.4 Gate 1 → §4；§5.3 切換 → §5；§5.4 降級 → §3.2；§5.5 任意模型 → §3.4；§6.3 不支援模式 → §3.3；§6.4 schema → §3.4；§7.2 數量 → §4；§8.2 Monitor/逾時/取消 → §6；§8.3 存檔 → 腳本；§9 錯誤表 → §6 步驤 5。

- [ ] **Step 3: 確認 frontmatter 可被 Claude Code 讀到**

重啟 Claude Code 後，可用的 skill 清單（system reminder）中應出現 `fal-generate` 及其 description。若沒有，檢查 frontmatter 是否為檔案最前三行、`---` 成對。

---

### Task 8: 驗收——對話流程手動測試

**Files:** 無新增；會建立 `$SKILL/config.json` 與 `{save_root}\image\*.jpg`

**Interfaces:**
- Consumes: Task 1–7 全部

- [ ] **Step 1: 初始化路徑**

確認 `$SKILL/config.json` 不存在。在對話輸入：「幫我生一張在草地上的柯基圖片」
Expected 依序：問存檔資料夾 → 問門檻 → 「已初始化…預設適中」→ Gate 0 卡片「圖片 · 文生圖」→ Gate 1 卡片顯示「適中 Nano Banana 2｜1 張｜預估 $0.08｜餘額 $…」

- [ ] **Step 2: 換等級後執行（約 $0.003）**

在 Gate 1 選「換等級」→ 選「便宜 FLUX Schnell」→ 新 Gate 1 顯示 $0.003 → 確認執行
Expected：對話中出現「已送出」「生成中…」「已存檔」逐步訊息（非一次全出）→ 完成訊息含路徑與餘額 → 對話中看到圖 → `config.json` 的 `last_output.image` 為該路徑，且 `categories.image.current` 仍為 `medium`（換等級只影響本次）

- [ ] **Step 3: 持久切換**

輸入：「圖片切成便宜的」
Expected：回覆已切換；`config.json` `categories.image.current == "low"`

- [ ] **Step 4: 改圖模式與不支援模式的替代（約 $0.08，先告知）**

輸入：「把剛剛那張改成戴紅色帽子」
Expected：Gate 0「圖片 · 改圖，底圖：{last_output}」→ Gate 1 註明「便宜 不支援改圖，本次改用 適中 Nano Banana 2 $0.08」→ 確認 → 事件中出現「輸入檔已上傳」→ 完成，圖中柯基戴紅帽；`current` 仍為 `low`

- [ ] **Step 5: 取消路徑（不扣費）**

Gate 0 選「取消」與 Gate 1 選「取消」各一次
Expected：兩次都結束流程，無任何 API 呼叫（無 SUBMITTED 訊息）

- [ ] **Step 6: 低額度警示（模擬）**

暫時把 `config.json` 的 `low_balance_threshold` 改成大於目前餘額的值（例如 9999），輸入「幫我生一張貓的圖」
Expected：Gate 1 出現「⚠️ 額度剩 $…」且方案為便宜；`current` 被寫成 `low`。測完把門檻改回。

- [ ] **Step 7: 設定指令**

輸入：「更新價格表」
Expected：列出每個模型的新舊價格；`config.json` 價格更新、`approx` 正確

- [ ] **Step 8: 清理**

刪除 scratchpad 中的 `payload_*.json`、`fal_test_out`、`test_upload.png`。保留 `config.json` 與使用者的輸出檔。

---

## Self-Review

**Spec coverage**：§1 目標 → Task 8；§2 檔案結構 → Task 1/2/6/7（tests/ 為額外新增，spec 未列但無衝突）；§3 觸發／Gate 0／初始化／Gate 1 → Task 7 §0–§4；§4 config 結構 → Task 6（多了 `version`、`heartbeat_sec`、`approx`，為實作需要）；§5 分級／分流／切換／降級／任意模型 → Task 7 §2/§3/§5；§6 模式／上傳／不支援替代／schema → Task 5、Task 7 §3.3–3.4；§7 餘額／估算 → Task 0、Task 7 §3.2/§4；§8 腳本介面／Monitor／存檔 → Task 2–5、Task 7 §6；§9 錯誤 → Task 2–5 的 Fail 路徑與 Task 7 §6 步驤 5；§10 測試 → 各 Task 測試步驤與 Task 8；§11 範圍外 → 未實作，符合。

**Placeholder scan**：無 TBD/TODO；SKILL.md 中 `{...}` 為執行期由 Claude 填入的變數，非計畫占位。

**Type consistency**：腳本參數名 `-PayloadFile/-OutDir/-Category/-InputFile/-UploadOnly/-PollIntervalSec/-HeartbeatSec/-TimeoutSec` 在 Task 2 定義、Task 7 §6 引用一致；JSON 結果欄位 `status/files/remote_urls/request_id/elapsed_sec/stage/message/cancel_url/status_url/response_url` 在 Task 3–4 產生、Task 7 §6–7 消費一致；config 鍵 `current/tiers/endpoints/price.amount/price.unit/price.approx/last_output/schema_cache/save_root/low_balance_threshold/timeout_sec/poll_interval_sec/heartbeat_sec` 在 Task 6 定義、Task 7 引用一致；mode 鍵名 `generate/edit/text_to_video/image_to_video/text_to_3d/image_to_3d` 在 Task 1、6、7 一致。
