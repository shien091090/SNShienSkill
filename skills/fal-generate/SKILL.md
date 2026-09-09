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
  - 類別為 `sfx` → 此降級規則不適用（sfx 只有一個模型，沒有更便宜的等級可切），略過「改用 low／寫回 current」的步驟；但仍在 Gate 1 卡片加上下面的餘額警告行讓使用者知情
  - 其餘類別，若 tier ≠ low → 本次改用 `low`，並將 `config.categories[類別].current = "low"` 寫回
  - 不論 tier 為何（含 sfx），Gate 1 卡片加一行「⚠️ 額度剩 ${balance}，低於門檻 ${threshold}」（使用者手動切回較貴方案時，每次都會再看到這行）
- 失敗（401/403/網路）→ 卡片加一行「（餘額查詢失敗：{原因}，略過自動降級）」，繼續

### 3.3 決定端點

sfx 沒有 tier/mode 分支，直接 `endpoint = config.categories.sfx.single.endpoints.generate`，不套用以下的一般公式（也沒有其他等級可以往上找）。

其餘類別：`endpoint = config.categories[類別].tiers[tier].endpoints[模式]`。

為 `null`（該等級不支援此模式）→ 依序往 `medium`、`high` 找第一個非 null 的端點，改用該等級**僅此一次**（不寫回 config），並在 Gate 1 卡片註明「{原等級} 不支援{模式}，本次改用 {替代等級} {label}」。**例外**：category=3d 且 mode=text_to_3d 時不適用此規則，改用下面的專屬規則；其餘所有類別/模式組合（例如 image 的 `edit` 在 low 等級為 null）仍照此規則處理。

**3d 的 text_to_3d 專屬規則**（取代上一段的一般規則，僅適用於這個組合，不做「往上找等級」的搜尋）：當目前 3d 等級的 `text_to_3d` 為 `null`（medium、low 皆是如此）時，改走兩段式流程：

1. 先以 `image` 類別目前等級的 `generate` 生一張參考圖（payload 加 `"aspect_ratio":"1:1"` 或 `"image_size":"square"`）。
2. 再以該圖，用**同一個** 3d 等級（也就是使用者原本所在的 medium 或 low——這兩個等級的 `image_to_3d` 皆非 null，只有 `text_to_3d` 是 null）走 `image_to_3d`。

Gate 1 卡片分兩行列出兩段費用，總計後確認一次；第一段完成後不再另外確認，直接進第二段。第一段產生的參考圖會更新 `config.last_output.image`（它是真實可用的生成圖檔，路徑已知，不只是內部暫存），第二段的 GLB 依 §7 一般規則更新 `config.last_output.3d`。

### 3.4 使用者指定任意模型（「切換到 XXX 模型」「用 XXX 生」）

1. 以 WebFetch 查 `https://fal.ai/models/{猜測的 endpoint}`；不確定 ID 時先 WebSearch `fal.ai models {名稱}` 取得正確 endpoint
2. 用 WebFetch 抓 `https://fal.ai/api/openapi/queue/openapi.json?endpoint_id={endpoint}`，取 required 欄位、輸入檔欄位名、輸出 URL 路徑，寫入 `config.schema_cache[endpoint]`（含 `fetched_at`）
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
| speech | 文本字數（含標點） | — | `amount × ceil(字數/1000)`；tier=low（Chatterbox）且字數 > 300 時，本次改用 medium（ElevenLabs Turbo v2.5，無字數上限），**僅此一次**（不寫回 config），並在 Gate 1 卡片註明「low 字數超過 300 上限，本次改用 medium {label}」 |
| 3d | — | 1 | `amount`（Hunyuan 需 PBR 時 +0.15） |

Gate 1 卡片（AskUserQuestion，單選）：

> 問題：「【{類別} · {模式}】{等級中文}方案 {label}｜{數量說明，如 1 張 / 5 秒 / 1 首 / 128 字}｜預估 ${費用}{approx 時前綴「約」}｜餘額 ${balance}{警告行}{替代方案說明行}{兩段式費用明細}」
> 選項：`確認執行` / `換等級` / `取消`（類別為 sfx 時不提供「換等級」，選項只有 `確認執行` / `取消`）

「換等級」→ AskUserQuestion 列 `高品質 {label} ${price}` / `適中 …` / `便宜 …`，選後**只影響本次**（不寫回），重算費用再出一次 Gate 1。sfx 沒有分級（只有一個模型），不提供此選項——沒有其他等級可換。

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

上面三種切等級指令（切成貴的／便宜的／適中），若類別（明講或依同句生成指令推斷）為 `sfx` → 回覆「音效沒有分級」，不寫入 `current`（sfx 只有一個模型，沒有等級可切）。

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
   - `status=ok` 且 `files` 非空 → §7
   - `status=ok` 但 `files` 為空陣列 → 不進入 §7；回報 `note` 的內容給使用者，並告知若需檢查原始 API 回應可查看 `raw` 欄位
   - `status=error` → 依 `stage` 說明：`auth` 教設定 FAL_KEY；`submit` 顯示 message（常見：422 參數錯 → 檢查 payload；404 端點不存在 → 建議「更新價格表」或指定其他模型；403/402 餘額不足）；`poll`/`result` 顯示 message 與 request_id；`download` → 若錯誤 JSON 的 `files` 欄位非空，先告知使用者這些檔案已成功存到本機（列出各檔案的本機路徑），再列出其餘 `remote_urls` 請使用者手動存；若 `files` 為空則只列出 `remote_urls`。**不自動重試**，問「要換等級再試一次嗎？」
   - `status=timeout` → AskUserQuestion「已等待 {timeout_sec} 秒仍未完成（fal 端仍在執行、會照常計費）。」選項：`再等一輪` / `取消任務` / `先不管它`
     - 再等一輪 → 再跑一次 Monitor，改用**續接模式**（不會重新送出）：

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/Users/user/.claude/skills/fal-generate/fal_run.ps1" -Endpoint "{endpoint}" -StatusUrl "{status_url}" -ResponseUrl "{response_url}" -RequestId "{request_id}" -OutDir "{save_root}" -Category {類別} -TimeoutSec {config.timeout_sec[類別]} 2>&1
```

       結果處理與一般流程相同（最後一行 JSON）
     - 取消任務 → 若 `cancel_url` 為 `null` 或缺失（例如「再等一輪」進入續接模式後第二次逾時——續接模式不帶 `-CancelUrl`，一律是 `null`）→ 回報「此輪無法取消（fal 仍在背景執行）」，不嘗試發送 PUT 請求；否則 PowerShell：`Invoke-RestMethod -Method Put -Uri '{cancel_url}' -Headers @{ Authorization = "Key $env:FAL_KEY" }`；回報「已送出取消」；若拋 400 → 回報「任務已完成、無法取消」並改走續接模式把結果抓下來
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
