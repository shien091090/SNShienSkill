# fal-generate Skill 設計文件

日期：2026-09-08
狀態：設計已與使用者確認，待寫實作計畫

## 1. 目標

讓使用者在 Claude Code 對話框用自然語言（「幫我生一張小狗的圖」「把剛剛那張改成戴帽子」「用這張圖做 5 秒影片」）呼叫 fal.ai 生成圖片／影片／音樂／音效／語音／3D，流程為：

1. 偵測生成意圖 → 確認類別與模式（Gate 0）
2. 查餘額、估算費用 → 使用者確認（Gate 1）
3. 呼叫 fal Queue API，每隔幾秒回報排隊／處理狀態
4. 回報成功／失敗
5. 產出檔案下載到本地固定資料夾

純本機 CLI 情境：API Key 存環境變數 `FAL_KEY`，不需要 proxy server，不使用 webhook。

## 2. 檔案結構

```
~/.claude/skills/fal-generate/
├── SKILL.md                 操作手冊（給 Claude 讀的流程說明）
├── config.json              持久化設定（初始化時建立；不進版控）
├── fal_run.ps1              輔助腳本：上傳輸入檔 → 送出任務 → 輪詢 → 下載
├── reference/
│   └── default-models.md    初始預設模型表與端點 ID（初始化時寫進 config）
└── docs/
    └── 2026-09-08-fal-generate-design.md   本文件
```

- `config.json` 放在 skill 目錄，跨對話持久保存
- API 呼叫全部由 `fal_run.ps1` 一支腳本完成；Claude 以背景執行 + Monitor 讀取腳本逐行輸出，再回報給使用者，不自行 sleep 迴圈輪詢

## 3. 觸發與確認流程

### 3.1 觸發條件

使用者訊息含生成意圖：「幫我生成／生一張／畫一個／做一段影片／配個音／唸一段／做個 3D 模型」等。SKILL.md 的 description 以此描述觸發。

### 3.2 Gate 0：類別 · 模式確認

Claude 先判斷：

- **類別**：`image` / `video` / `music` / `sfx` / `speech` / `3d`
- **模式**：見 §6
- **輸入檔**（若模式需要）：本機路徑，或「剛剛那張／上一張」→ 從 `config.last_output[類別]` 取

以 AskUserQuestion 呈現一張卡片，例如：

> 要用 fal 生成【圖片 · 改圖】嗎？底圖：`D:\FalOutputs\image\20260908_143012.png`
> 選項：對 / 換類別或模式 / 取消

判斷不出類別或缺少必要輸入檔時，卡片直接列出類別選項或詢問檔案路徑。

### 3.3 初始化（config.json 不存在時，只跑一次）

1. 依 `reference/default-models.md` 寫入所有類別的三級模型表，全部 `current = "medium"`
2. 問使用者存檔根目錄（例：`D:\FalOutputs`）
3. 問額度警示門檻（建議預設 $5）
4. 告知「已初始化，預設使用適中方案」

### 3.4 Gate 1：費用確認

依序執行：

1. 解析等級切換指令（§5.3）並寫回 config
2. 查餘額（§7.1）；低於門檻則依 §5.4 處理
3. 解析數量／時長／字數（§7.2），預設假設**直接列在卡片上**
4. 取得端點 schema（§6.4），組出 payload
5. AskUserQuestion 卡片：類別 · 模式 / 等級 + 模型 / 數量或時長 / 預估金額 / 目前餘額 / 警告（若有）
   選項：確認執行 / 換等級 / 取消

使用者確認後才呼叫 `fal_run.ps1`。

## 4. config.json 結構

```json
{
  "save_root": "D:\\FalOutputs",
  "low_balance_threshold": 5.0,
  "poll_interval_sec": 3,
  "timeout_sec": { "image": 180, "music": 180, "sfx": 180, "speech": 180, "video": 600, "3d": 600 },
  "last_output": { "image": "D:\\FalOutputs\\image\\20260908_143012.png", "video": null, "...": null },
  "schema_cache": {
    "fal-ai/nano-banana-2": { "required": ["prompt"], "optional": ["num_images", "aspect_ratio"], "fetched_at": "2026-09-08" }
  },
  "categories": {
    "image": {
      "current": "medium",
      "tiers": {
        "high":   { "label": "Nano Banana Pro", "endpoints": { "generate": "fal-ai/nano-banana-pro", "edit": "fal-ai/nano-banana-pro/edit" }, "price": { "amount": 0.15, "unit": "張" } },
        "medium": { "label": "Nano Banana 2",   "endpoints": { "generate": "fal-ai/nano-banana-2",   "edit": "fal-ai/nano-banana-2/edit" },   "price": { "amount": 0.08, "unit": "張" } },
        "low":    { "label": "FLUX Schnell",    "endpoints": { "generate": "fal-ai/flux/schnell",    "edit": null },                          "price": { "amount": 0.003, "unit": "張" } }
      }
    },
    "video":  { "current": "medium", "tiers": { "...": "..." } },
    "music":  { "current": "medium", "tiers": { "...": "..." } },
    "sfx":    { "single": { "label": "ElevenLabs SFX v2", "endpoints": { "generate": "fal-ai/elevenlabs/sound-effects/v2" }, "price": { "amount": 0.002, "unit": "秒" } } },
    "speech": { "current": "medium", "tiers": { "...": "..." } },
    "3d":     { "current": "medium", "tiers": { "...": "..." } }
  }
}
```

- `sfx` 不分級，只有 `single`
- `price.unit` 為計價單位：張 / 秒 / 首 / 分 / 千字 / 次
- `schema_cache` 快取端點必要／可選參數名稱，避免每次上網

## 5. 模型分級與切換

### 5.1 預設模型表（以熱門度為前提，價格為 2026-09 參考值）

| 類別 | 高品質 | 適中 | 便宜 |
|---|---|---|---|
| 圖片 | Nano Banana Pro $0.15/張 | Nano Banana 2 $0.08/張 | FLUX Schnell ~$0.003/張 |
| 影片 | Seedance 2.0 ~$0.30/秒 | Kling 2.5 Turbo Pro $0.07/秒 | Seedance 1.0 Lite ~$0.036/秒 |
| 音樂 | ElevenLabs Music $0.60/分（無條件進位） | MiniMax Music 2.6 $0.15/首 | MiniMax Music 1.5 $0.03/首 |
| 音效 | ElevenLabs SFX v2 $0.002/秒（不分級） | — | — |
| 語音 | MiniMax Speech-2.8 HD $0.10/千字 | ElevenLabs Turbo v2.5 $0.05/千字 | Chatterbox Multilingual $0.025/千字 |
| 3D | Hunyuan 3D Pro v3.1 $0.375/次 | Trellis 2 ~$0.30/次 | Trellis $0.02/次 |

選型依據：fal 各類別列表排序（依使用量）＋市場知名度；語音以中文表現為優先。各端點 ID 於實作時逐一驗證存在，並記錄在 `reference/default-models.md`。

### 5.2 音訊分流

使用者說「音效／sound effect／聲音效果」→ `sfx`；說「音樂／背景樂／一首歌／BGM」→ `music`。判斷不出時 Gate 0 問。

### 5.3 等級切換（持久化，只影響該類別）

| 使用者說法 | 動作 |
|---|---|
| 「切成貴的／高品質的」 | 該類別 `current = high` |
| 「切成便宜的／快的／不要求品質」 | `current = low` |
| 「切回適中／中等」 | `current = medium` |
| 「切換到 XXX 模型」（明確模型名） | 不受設定表限制，fal 任何模型皆可（§5.5） |

切換寫回 config，之後沿用。切換若與生成指令同句，先切換再生成。

### 5.4 低額度自動降級

每次 Gate 1 都查餘額。若 `balance < low_balance_threshold`：

- 該類別本次改用 `low`，並寫回 `current = low`
- 卡片顯示「⚠️ 額度剩 $X，已切為便宜方案」
- 使用者仍可手動切回較貴等級；只要餘額仍低於門檻，**每次生成都再提醒一次**
- 餘額查詢失敗（權限不足／網路）→ 提示原因，跳過降級，仍可繼續

### 5.5 使用者指定任意模型

1. 以使用者說的名稱在 fal 搜尋對應端點 ID（WebFetch `https://fal.ai/models/{id}` 或搜尋頁）
2. 抓該模型頁面定價；抓不到 → 告知「無法自動取得定價」，由使用者決定是否繼續
3. 抓 OpenAPI schema 取得參數名稱
4. 本次使用該模型；生成後問使用者是否要存進某個等級

## 6. 任務模式（Mode）

### 6.1 模式定義

| 類別 | 模式 | 判斷依據 |
|---|---|---|
| image | `generate` | 只有文字 |
| image | `edit`（含文字指令式局部修改） | 提到既有圖片：路徑或「剛剛那張」 |
| video | `text_to_video` / `image_to_video` | 有無輸入圖 |
| 3d | `text_to_3d` / `image_to_3d` | 有無輸入圖 |
| music / sfx / speech | `generate` | — |

不做遮罩式 inpainting（v1 範圍外）。

### 6.2 輸入檔上傳

模式需要輸入圖時，`fal_run.ps1 -InputFile <路徑>` 先透過 fal storage upload API 上傳，取得 URL 後填入 payload。

### 6.3 目前等級不支援該模式

不偷偷失敗：告知「便宜方案不支援改圖，這次改用適中方案 Nano Banana 2（$0.08/張）」，以替代方案計價，**不改動使用者設定的等級**，只影響本次。替代順序：同類別往上一級找第一個支援該模式的端點。

3D 純文字輸入且目前等級無 `text_to_3d`：先以圖片類別目前方案生一張參考圖再轉 3D，**兩段費用在卡片上分開列出**。

### 6.4 端點參數：OpenAPI schema

第一次用到某端點時抓 `https://fal.ai/api/openapi/queue/openapi.json?endpoint_id={id}`，把 required / 常用 optional 參數名快取到 `config.schema_cache`。之後組 payload 直接用快取。抓不到 schema → 以模型頁面 API 範例為準。

## 7. 費用估算與餘額

### 7.1 餘額查詢

```
GET https://api.fal.ai/v1/account/billing?expand=credits
Authorization: Key $FAL_KEY
→ credits.current_balance (USD)
```

需 **ADMIN scope** 的 key；ADMIN 包含 API 權限，因此使用者只需一把 ADMIN key 設為 `FAL_KEY`。SKILL.md 說明此點。

### 7.2 預估費用

`預估 = price.amount × 數量`，數量解析規則：

| 類別 | 數量來源 | 預設 |
|---|---|---|
| image | 「生 3 張」 | 1 張 |
| video | 「5 秒」 | 5 秒 |
| music | 依模型：/首 → 1；/分 → 目標長度無條件進位 | 1 首 / 1 分 |
| sfx | 「3 秒的音效」 | 5 秒 |
| speech | 文本字數 ÷ 1000 | 實際字數 |
| 3d | 次數 | 1 次 |

價格用 config 參考值，不每次上網。使用者說「更新價格表」→ 重新抓各模型頁面刷新 config。卡片上不確定的價格標「約」。

## 8. Queue 呼叫與進度回報

### 8.1 fal_run.ps1 介面

```
fal_run.ps1 -Endpoint <id> -PayloadFile <json 檔路徑> -OutDir <dir> -Category <cat>
            [-InputFile <path>] [-UploadOnly] [-PollIntervalSec 3] [-HeartbeatSec 15] [-TimeoutSec 180]
            [-StatusUrl <url> -ResponseUrl <url> -RequestId <id>]   # 續接模式：逾時後不重新送出，直接輪詢既有任務
```

payload 以 UTF-8 JSON **檔案**傳入（由 Claude 用 Write 寫到 scratchpad），避免中文與引號經過 shell 轉義。payload 內以字串 `__INPUT_FILE_URL__` 佔位，腳本上傳後替換為實際 URL。

流程：

1. 檢查 `FAL_KEY`；缺少 → 印出設定說明，exit 2
2. 有 `-InputFile` → 上傳（`POST https://rest.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3` → `PUT upload_url`），以 `file_url` 替換佔位字串；`-UploadOnly` 則印出 `file_url` 後結束
3. `POST https://queue.fal.run/{endpoint}` → 取得 `request_id`、`status_url`、`response_url`（**使用回傳的 URL**，不自行拼接：多層路徑端點的 status URL 只含 app 根路徑）
4. 每 `PollIntervalSec` 秒查一次 status；**狀態改變時印一行，否則每 `HeartbeatSec` 秒印一行心跳**（Monitor 對事件量有上限，每 3 秒印一行會被停掉）：
   ```
   [00:03] IN_QUEUE position=2
   [00:06] IN_PROGRESS
   [00:21] IN_PROGRESS
   [00:34] COMPLETED
   ```
   腳本輸出一律英文，由 Claude 翻成中文回報（避免 PowerShell 5.1 中文編碼問題）
5. `GET .../requests/{id}` 取結果，下載所有輸出檔到 `OutDir`
6. 最後一行印 JSON：`{"status":"ok","files":[...],"elapsed_sec":14,"request_id":"..."}`
7. 失敗：`{"status":"error","stage":"submit|poll|download","message":"...","request_id":"...","remote_urls":[...]}`，exit 1
8. 逾時：`{"status":"timeout","request_id":"..."}`，exit 3（**不取消任務**）

### 8.2 Claude 端

- 以 **Monitor 工具**執行腳本（`powershell.exe -NoProfile -ExecutionPolicy Bypass -File fal_run.ps1 ...`），每行 stdout 即一個事件通知；`timeout_ms = (TimeoutSec + 30) × 1000`。收到事件即翻成中文回報使用者；最後一行為 JSON 結果
- 逾時 → AskUserQuestion「繼續等 / 取消任務」；取消呼叫 `PUT .../requests/{id}/cancel`
- 成功 → 更新 `config.last_output[類別]`，回報：本地路徑、耗時、預估花費、目前餘額（再查一次）

### 8.3 存檔規則

`{save_root}/{類別}/{yyyyMMdd_HHmmss}.{副檔名}`；多檔加 `_01`、`_02`。副檔名依回傳 URL 或 content-type。

## 9. 錯誤處理

| 情況 | 處理 |
|---|---|
| 無 `FAL_KEY` | 告知設定方式，不呼叫 |
| 單次 status 查詢網路失敗 | 腳本內重試 3 次（間隔 2 秒）後才判定失敗 |
| fal 回傳 FAILED | 顯示錯誤訊息，**不自動重試**（fal 伺服器端已有最多 10 次重試），問是否換等級再試 |
| 下載失敗但生成成功 | 印出遠端 URL 讓使用者手動存 |
| 餘額查詢失敗 | 提示，跳過降級，繼續 |
| 端點不存在（404） | 告知端點 ID 可能已變更，建議「更新價格表」或指定其他模型 |

## 10. 測試

- `fal_run.ps1`：以 FLUX Schnell（最便宜）做 smoke test：submit → poll → download 全流程；模擬無 `FAL_KEY`、錯誤端點、逾時（TimeoutSec=1）三種失敗路徑
- 初始化：刪除 config.json 後跑一次，確認寫入結構正確
- 端點驗證：對預設表所有端點 ID 抓 OpenAPI schema，確認皆存在
- 對話流程：以「生一張小狗」「把剛剛那張改成戴帽子」「切成便宜的」「用 X.png 做 5 秒影片」四句手動走一輪

## 11. 範圍外（v1 不做）

- 遮罩式 inpainting
- Webhook 模式
- 語音克隆、參考影片生成（reference_to_video）
- 多帳號 / 多把 key
