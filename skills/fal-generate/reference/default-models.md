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

> 註：FLUX Schnell 官方頁面實際以「每百萬像素 $0.003」計價（非固定每張），`landscape_4_3` 預設輸出約 0.86MP，換算每張略低於 $0.003，故表中維持 `(約)`。

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

> 註：Kling 2.5 Turbo Pro 官方頁面原文為「5s 影片 $0.35，之後每秒加收 $0.07」，換算後與表中 0.07/秒 一致（已確認，非估算）。
> 註：Seedance 2.0 官方頁面實際以「每 1000 tokens」計價（480p/720p/1080p 為 $0.014/1000 tokens，4K 為 $0.008/1000 tokens），與秒數非線性對應，故表中 0.30/秒 維持為 `(約)` 估算值，非官方原文換算。

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
