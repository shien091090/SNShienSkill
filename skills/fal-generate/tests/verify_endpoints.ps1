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
