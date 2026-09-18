---
name: deck-pipeline
description: 觸發詞「做簡報」或 /deck-pipeline <資料夾路徑>。把一個堆滿簡報素材 (截圖、txt、md、語音檔) 的資料夾, 經六個階段 (堆素材 → 分 topic → 講稿 → 頁面內容 → 版型定案 → 生 pptx) 帶到可編輯 pptx。跨多次會話進行, 進度靠資料夾內 STATUS.md 銜接。使用者提到要做簡報、整理簡報素材、寫講稿、把講稿變投影片、或指向一個已有 STATUS.md 的資料夾時使用。
---

# deck-pipeline

一個資料夾, 六個階段做出 `output/<title>.pptx`, 使用者拍板、AI 動手。排版美化不在這六階段範圍內, 由使用者自行處理 (例如手動送桌面版 Claude Design), 完成後放回 `output/`。輸入輸出都在同一個資料夾原地演化, 與任何專案無關。

格式規格在 `references/formats.md`, 階段 5 細節在 `references/stage-style.md`, 需要時才讀。

## 每次呼叫的固定開場

1. 拿到資料夾路徑 (參數沒帶就問)。資料夾不存在就停下來問
2. 讀 `STATUS.md`。不存在 → 視為 collect 起點, 建立它。格式損壞 → 回報, 問使用者重建還是手修, 不自行猜
3. 比對 stage 與資料夾實況 (例如 stage: organize 但根目錄已有 SLIDES.md)。有打架 → 回報差異, 以使用者裁決為準更新 STATUS.md
4. 回報一句: 「目前在 X 階段, Y 個 topic, 其中 Z 個講稿完成」
5. 問: 繼續當前階段, 還是回頭改前面的東西

## 互動原則

- 全部純文字對話, 不用 AskUserQuestion 選單
- 逐 topic 確認, 不一次產完整份再問
- 提案先給結論與理由, 使用者拍板才動檔案
- 所有素材必須是資料夾裡的檔案, 不存在「只在對話裡講過」的素材 (見「素材規則」)

## 資料夾樣貌

```
<deck>/
  STATUS.md            進度與 topic 表
  (散檔)               階段 1 堆放區
  01_<topic>/          階段 2 後: 素材搬進來, 前綴即順序
    週會.m4a           語音素材與它的逐字稿永遠同層同名 (見「語音素材」)
    週會.md
  _unsorted/           決定不用的素材, 不刪
  _archive/            被拆分過的原始檔 (逐字稿被拆時音檔跟著進來), 不刪
  SCRIPT.md            講稿, 單一檔
  SLIDES.md            頁面內容, 單一檔
  IMAGES_TODO.md       待補圖清單 (腳本產生)
  STYLE.md             版型規則
  output/<title>.pptx        階段 6 build 產物; 使用者美化後可能放回其他檔名的版本
```

## 六階段

### 1. collect 堆素材

- 做: 建立 STATUS.md (`stage: collect`)。素材由使用者自行堆放, AI 不動
- 使用者說堆好了 → 先掃語音檔, 不要直接轉 organize:

```
py -3 ~/.claude/skills/deck-pipeline/scripts/transcribe.py <deck> --scan --prompt 詞1,詞2
```

  - 沒有語音檔 → 直接往下
  - 有 → **先走「確認專有名詞」那一節**, 這是轉錄前的必經步驟
  - **把 `--scan` 的表格和花費估算貼給使用者, 問要走 Scribe 還是本地**。這是必問的一題, 因為 Scribe 花的是使用者的錢:

```
找到 N 個語音檔, 總長 59:54, 走 Scribe V2 估計花費 US$0.62 (含 keyterms 加價 30%)
要走 Scribe (品質好、有標點) 還是本地 Breeze (免費, 但沒標點、專有名詞常錯)?
```

  - 使用者說走線上 → `--scribe`; 說不要花錢 → `--local`。**不指定引擎腳本會直接 exit 2 拒絕執行**, 這是刻意的, 防止跳過詢問
  - 轉完把逐字稿貼幾段給使用者確認辨識品質, 明顯錯的詞請他直接改 `.md` (腳本不會覆蓋已存在的逐字稿)
- 完成: 語音檔都有逐字稿了 → stage 改 organize

### 2. organize 分 topic

- 讀全部散檔: 截圖用 Read 看圖, 文字檔讀內容。檔案多就用 subagent 平行讀回摘要
- 語音檔不直接讀 (讀不了), 讀它同層同名的 `.md` 逐字稿。還有語音檔沒逐字稿 → 回頭補跑 collect 的轉錄步驟
- 提出 topic 切分與順序, 附每份素材的歸屬建議, 標出需要拆分的檔
- topic = 講述段落, 不等於素材資料夾。使用者的素材常已按主題預分好資料夾, 提案以 3~5 個敘事層 topic 為底 (例如: 以往怎麼做 / 這次怎麼做 / 流程展開 / 痛點與下一步), 既有資料夾當 topic 底下的步驟保留, 加 `N_` 前綴排序; 不要一個資料夾一個 topic
- 提拆分方案時逐段貼出每一份拆分後的原文, 不寫「第 N~N 行」, 使用者看不出內容
- 不要為了 parser 改資料夾名 (路徑帶括號、空白都能 parse); 改名只在使用者要求或要加排序前綴時做
- 使用者反覆調整到滿意才動檔
- 定案後: 建 `01_<topic>/` 子資料夾、搬檔 (不複製)、拆分 (見素材規則)、不用的進 `_unsorted/`、寫 STATUS.md topic 表
- 完成: 根目錄除 STATUS.md 與流程檔 (SCRIPT.md / SLIDES.md / IMAGES_TODO.md / STYLE.md) 外沒有散檔; `_archive/` 每個**文字檔**都對得到至少一個拆分檔 (音檔不算, 它是陪逐字稿一起進去的) → stage 改 script

### 3. script 講稿

- 逐 topic 寫 `SCRIPT.md`, 每個 topic 一個 `## 01 <topic>` 章節
- 內容是演講重點條列, 密度是「講者在備忘稿上一眼看懂接下來要講什麼」: 一個 topic 3~6 條, 每條一句, 可帶「這邊放 xxx.png」註記。不寫長文、不鋪陳、不寫講稿逐字稿。不是要放上投影片的字, 但也不是文章
- 開寫前先問聽眾是誰、時長、簡報標題, 記進 SCRIPT.md 檔頭與 STATUS.md title
- 自己補的觀點 (原素材沒有的) 標 `[待確認]`, 由使用者決定留不留
- 每個 topic 寫完停下給使用者看, 回饋修改後才往下一個; STATUS.md 該 topic `script` 欄 doing → done
- 完成: 全部 topic `script: done` → stage 改 slides

### 4. slides 頁面內容

- 從 SCRIPT.md 出發, 逐 topic 擬頁面寫進 `SLIDES.md`, 格式見 `references/formats.md`
- 每頁只留最核心的字, 能用圖就用圖。有現成截圖就填路徑, 沒有就寫圖片描述、路徑填 `TODO`, 描述要具體到能拿去找圖或生圖
- 沒有截圖但「畫得出來」的圖 (架構示意、流程圖、比喻圖、icon 方塊) 不要留 TODO 給使用者找圖: 由 AI 依描述寫成 `.svg` 落在該 topic 資料夾, 路徑填進 SLIDES.md, build 時會轉成可編輯的 PowerPoint 原生圖案。SVG 撰寫規則見 `references/formats.md`。真的需要照片/實機截圖的才留 TODO
- 用 `> ` 註記對應講稿段落, 會進 speaker notes
- 版型可以在這階段新增: 內容需要現有六種以外的排法 (兩圖並排、主圖加多個圖示、三欄以上表格) 就直接取名用 (`image2` / `image-icons4` / `table` 這類), 記進 STATUS.md log, 階段 5 照清單出方案
- 逐 topic 確認; STATUS.md 該 topic `slides` 欄 doing → done
- 全部完成後跑 `py -3 ~/.claude/skills/deck-pipeline/scripts/build_pptx.py <deck> --images-todo` 產 IMAGES_TODO.md, 告知使用者哪些圖要補。補圖不在 skill 範圍, 沒補的圖 build 時會是灰框
- 完成: 全部 topic `slides: done` → stage 改 style

### 5. style 版型定案

照 `references/stage-style.md` 做。摘要: 歸納 SLIDES.md 用到的版型 → 問風格方向 → design skill 出 canvas (每版型 2~3 方案) → 使用者挑選微調 → 轉寫 STYLE.md → 使用者確認 → stage 改 build。

### 6. build 生 pptx

```
py -3 ~/.claude/skills/deck-pipeline/scripts/build_pptx.py <deck>
```

- 成功: `output/<title>.pptx`, 文字皆可編輯, TODO 圖為灰框加描述, `>` 進 notes
- 失敗: 腳本列出全部錯誤 (版型未定義 / 圖片不存在), 修 SLIDES.md 或 STYLE.md 後重跑
- 改了 SLIDES.md 或 STYLE.md 就重 build, 每次整份重建
- 相依: `py -3 -m pip install python-pptx pyyaml` (SVG 轉換器已 vendor 在 scripts/vendor, 不用另裝)
- pptx 正在 PowerPoint 裡開著會 build 失敗 (PermissionError), 先請使用者關掉再重跑
- STYLE.md 用到的字型播放機器要裝, 沒裝 PowerPoint 會退系統字; 定案時提醒使用者
- 完成: 使用者確認內容無誤 (字、圖、頁序) → stage 改 done。build 到此結束, 排版美化由使用者自行處理 (例如手動送桌面版 Claude Design), 完成的檔案放回 `output/`

## 素材規則 (所有階段適用)

任何時候新增素材都走同一套: 落檔 → 歸 topic → STATUS.md 該 topic 備註記 `+素材 <日期> <檔名>`。還沒有 topic 就放根目錄等分類。

- **使用者請 AI 收集**: WebSearch / WebFetch 找, 每份內容一個 md 檔, 檔頭記來源 URL 與抓取日期。網路圖片用 PowerShell 下載成檔案, 來源 URL 記進 STATUS.md log
- **對話補述**: 使用者在對話裡講的補充, 當場寫成 `note_<主題關鍵字>.md`
- **拆分**: 一份文字檔內文跨多個 topic 時, 拆成 `<原檔名>__<topic關鍵字>.md`, 每個拆分檔檔頭記「拆自: <原檔名>, 第 X~Y 段」; 原檔搬進 `_archive/` 不刪。原檔是逐字稿時, 同名音檔跟著一起進 `_archive/`
- **語音檔**: 見下面「語音素材」一節

## 語音素材

語音檔 (`.mp3 .wav .m4a .flac .ogg .aac`) 由 `scripts/transcribe.py` 轉成**同層同名的 `.md` 逐字稿**, 之後所有階段只讀逐字稿, 完全當一般文字素材處理, 不知道它從語音來。

```
py -3 ~/.claude/skills/deck-pipeline/scripts/transcribe.py <deck> --scan [--prompt 詞1,詞2]
py -3 ~/.claude/skills/deck-pipeline/scripts/transcribe.py <deck> --scribe [--prompt 詞1,詞2]
py -3 ~/.claude/skills/deck-pipeline/scripts/transcribe.py <deck> --local  [--prompt 詞1,詞2] [--cpu]
```

- `--scan` 只列表不轉錄, 並印出走 Scribe 的花費估算
- **`--scribe` / `--local` 二選一, 不給會 exit 2**。哪一條要由使用者決定, 見下面「引擎怎麼選」
- **已存在同名 `.md` 就跳過**, 所以可以隨時重跑, 也不會蓋掉使用者手改過的逐字稿
- 全部都有逐字稿時完全不載入模型也不呼叫 API, 秒退
- 逐字稿是純文字段落不帶時間戳, 檔頭三行記 `轉自 / 模型 / 轉錄日期`
- **音檔永遠跟它的完整逐字稿同一層** — 沒被拆就一起進 topic 資料夾, 被拆了就跟原逐字稿一起進 `_archive/`。只有這一條規則, 沒有例外
- 路徑一律給 Windows 格式 (`C:\...`), 給 Git Bash 的 `/c/...` 會被 Python 解成別的目錄, 而且不會報錯, 只會安靜地掃不到檔

### 轉錄前一定要先確認專有名詞

**沒跟使用者確認過專有名詞就不要開始轉錄。** 專有名詞是辨識錯誤的最大來源, 而且是事後最難補的 —
內容講錯你看得出來, 人名公司名講錯你看不出來, 會整份帶著錯進講稿。

keyterms 沒有存檔機制 (2026-09-14 使用者裁決: 用流程規則取代檔案機制), 所以每次都要重新確認。
流程是**AI 先提案, 使用者修正**, 不是叫使用者憑空生一份清單:

1. **先探測每個音檔的主題與語言** — 這一步免費, 不要跳過:

```
每個檔抽 60 秒 (取 1/4 處, 避開開場致詞) → 本地 faster-whisper large-v3 跑一次
→ 看 info.language 與內容大意
```

   實測 21.8x realtime, 六個檔探測不到一分鐘。**這一步救過兩次**:
   - 一次抓到某個檔其實是**日文**演講, 照預設 `language_code: zho` 送出去會整份壞掉
   - 一次推翻了「檔名編號 = 議程順序」的假設, 六個檔實際主題跟議程表對不起來

2. **從探測內容組出候選詞表**, 一個音檔一組。必要時再 WebSearch 補 (講座名、講者、產品、公司)
3. **把候選清單貼給使用者確認**, 由他增刪。他答不出來也沒關係, 用 AI 組的那份就好, 但**一定要讓他看過**
4. 定案後才跑轉錄。詞表順手寫進當次的執行紀錄或 STATUS.md log, 之後要重跑有依據

> Scribe 的 `keyterms` 上限 100 個詞、每個 50 字元; Breeze 是塞進 `initial_prompt`, 太長會被截斷, 控制在 30 個以內。

### 引擎怎麼選 (每次都要問使用者)

判準**不是**機密性, 是**要不要花使用者的錢**。所以流程固定是: `--scan` 出估價 → 問使用者 → 照回答執行。不准自己選。

| | `--scribe` (ElevenLabs Scribe V2 via fal) | `--local` (Breeze-ASR-25) |
|---|---|---|
| 費用 | $0.008/分鐘, 加 keyterms 再 +30% (一小時約 US$0.62) | 免費 |
| 速度 | 一小時約 3 分鐘 (含四段上傳) | 一小時 18~28 分鐘 |
| 標點 | 有 (一小時 316 句號 / 1171 逗號) | **完全沒有** |
| 輸出 | 簡繁混雜, 腳本用 OpenCC `s2tw` 轉繁 | 原生繁體 |
| 非語音段 | 標成 `[笑]` `[遊戲音效]` `[背景雜音]` | **爆重複迴圈幻覺** |
| 專有名詞 | `keyterms` 參數 (最多 100 個) | `initial_prompt` 偏方 |
| 需要 | `FAL_KEY` 環境變數 (User scope) | 4GB 模型 + CUDA |

實測同一場一小時講座 (TGDF, 台灣中文夾大量英文術語), 品質差一個檔次:

| Breeze | Scribe V2 |
|---|---|
| Lexington **IndieFlight** | **Indie Prize** |
| **旅行式**遊戲相關**體力** | **敘事遊戲**相關**領域** |
| 它是一群**網** | 它是一幅**畫** |
| 小小的 **iPad** / 這個 **iPhone** | 小小的 **icon** |
| **虎中帶雷** | **苦中帶淚** |
| **營救**葬禮 | **宇宙**葬禮 |

結論: Breeze 那份「要重寫」, Scribe 那份「要校對」。但兩份的人名/機構名都還是會錯, **專有名詞一律要人工校對**, 不要當成正確的直接用進講稿。

`--local` 的已知缺陷**不修, 這是刻意的** (2026-09-14 使用者裁決): 非語音段 (播影片、長靜音) 會爆重複迴圈幻覺, `collapse_repeats` 也擋不住夾雜標點的變體 (例如 `：SIGONO：：SIGONO：`)。它的定位就是「不想花錢時的堪用備案」, 要品質就走 `--scribe`。想修的話方向是接 Silero VAD 先切掉非語音段, 但不要自己動手, 先問使用者。

### Scribe 的硬限制與坑

- **單段音檔上限 1200 秒**, 超過回 422 `audio_duration_too_long`。腳本內建切成 900 秒一段再把時間戳偏移合回去 (`split_plan` / `words_to_segments`), 使用者不用自己切
- 回傳的是純文字 JSON 不是檔案, 所以結果在 `fal_run.ps1` 最後一行的 `raw` 欄位, `files` 會是空的, 那不是失敗
- **不要用 pipe 直接 capture fal_run.ps1 的 stdout**, 中文會變 Latin-1 亂碼 (`[笑]` → `[ç¬]`)。腳本改成 `| Out-File -Encoding utf8` 再讀檔; `repair_mojibake()` 是最後一道保險, 不要依賴它
- `keyterms` 不是萬靈丹: 實測餵了 SIGONO 還是被聽成 Game Award, 因為講者把英文名混在中文句子中間念
- **腳本寫死 `language_code: zho` 並套 OpenCC 轉繁, 只適用中文音檔**。碰到日文/英文演講必須另外處理 (改 `language_code` 並跳過 `to_traditional_tw`), 不能直接丟進去。所以上面那個「先探測語言」的步驟是必要的, 不是可選的

### 分段怎麼決定

三條規則疊在一起 (`merge_segments`), 兩種引擎共用:

1. 停頓 ≥ 1.0 秒且段落已滿 100 字 → 換段。**只有 Scribe 的 word 級時間戳有真實停頓** (一小時 108 次); whisper 系的長檔時間戳是連續的 (前段結束即後段開始), 這條幾乎不觸發
2. 超過 200 字且停在句末標點 → 換段。Breeze 沒標點所以等於沒有
3. 超過 400 字 → 在 segment 邊界硬換。保底用, Breeze 幾乎全靠這條

實測一小時講座: Scribe 切出 97 段中位 205 字; Breeze 切出 57 段全靠第 3 條。

### 相依與環境

**這些東西都不在 git 裡, 換一台機器要重裝一次。** git 只有 skill 本體 (29 個檔)。

```
py -3 -m pip install av opencc-python-reimplemented    # 必裝: 解碼 + 簡轉繁
py -3 -m pip install faster-whisper                    # 轉錄前的「探測音檔」那步要
py -3 -m pip install transformers torch                # 只有 --local 要
```

- **探測那步也要 torch**: faster-whisper 走 CUDA 時要借 torch 自帶的 `cublas64_12.dll` (見下面那條), 只裝 faster-whisper 會退 CPU。只用 `--scribe` 的人若不想裝 torch (2.7GB), 探測就在 CPU 跑, 60 秒的片段還是幾秒內出來, 可以接受
- 模型是第一次跑才下載到 `~/.cache/huggingface`, 不隨 git 走。兩個各約 2.9 GB:
  `Breeze-ASR-25` (`--local` 用) 與 `faster-whisper-large-v3` (探測用)。
  選型時還下載過 `asadfgglie/faster-whisper-large-v3-zh-TW` (1.5 GB), **已淘汰並刪除**, 不要再裝回來
- 解碼走 PyAV, **不需要系統裝 ffmpeg** (PyAV 自帶), 所以 m4a/aac 也直接吃
- `--scribe` 需要 `FAL_KEY` 設在 **User scope** 環境變數 (`[Environment]::SetEnvironmentVariable("FAL_KEY","<key>","User")`), 腳本每次呼叫都從 User scope 讀, 所以設完不用重開 Claude Code
- `--local` 首次跑會下載約 4GB 模型到 HuggingFace cache; 有 CUDA 自動用 GPU (bfloat16, 約 4.4GB VRAM), 沒有就退 CPU 並明講會很慢
- **Windows 長路徑**: 裝 torch 會因為 260 字元上限失敗 (Microsoft Store 版 Python 的 site-packages 前綴就 137 字元)。要用系統管理員權限開:
  `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1`
- RTX 50 系 (Blackwell, sm_120) 要 CUDA 12.8 的 torch 輪子: `pip install torch --index-url https://download.pytorch.org/whl/cu128`。實測 sm_120 的 bfloat16 推論沒問題
- CTranslate2 (faster-whisper 底層) 在 sm_120 也跑得動, 但要先 `os.add_dll_directory(<site-packages>/torch/lib)` 掛上 torch 自帶的 `cublas64_12.dll`, 否則 `Library cublas64_12.dll is not found`

### OpenCC 用 s2tw 不用 s2twp

`s2twp` 的慣用詞轉換會把**「文本」改成「文字」**, 在遊戲業是錯的。用 `s2tw` 只轉字不轉詞。另外 OpenCC 一律產出「臺」, 台灣慣用「台」, 所以 `to_traditional_tw()` 最後再換一次。

## 回頭修改

允許回到任何前面階段。改動後, 在 STATUS.md 對應 topic 的後續階段欄位標 `stale`, 提醒要重看。stale 不阻擋 build。

改 topic 順序或改 topic 名稱時的檢查清單, 一項一項確認:
- 資料夾改名 (`NN_<topic>`)
- SLIDES.md 的 `## NN <topic>` 與該 topic 下所有圖片路徑
- SCRIPT.md 章節標題
- STATUS.md topic 表
- 後續階段欄位標 `stale`
- 重跑 `--images-todo`

## 錯誤處理

- STATUS.md 損壞: 問使用者, 不自行重建
- stage 與資料夾實況打架: 回報, 使用者裁決
- design skill 不可用: 階段 5 退化為文字描述方案 (見 stage-style.md 第 6 節)
- build 失敗: 一次列全部錯誤, 不逐個中斷

## 維護這支 skill

- 改 `scripts/` 前後都跑 `py -3 -m pytest scripts/tests` (現為 101 筆)
- `transcribe.py` 有兩處沒被 pytest 蓋到, 因為一個要載 4GB 模型、一個會真的花錢: `make_breeze_transcriber()` 與 `make_scribe_transcriber()` / `_call_fal_scribe()`。動到它們要另外跑一次真實音檔 smoke test。其餘純邏輯 (掃檔/併段/估價/切檔計畫/word 轉 segment/簡轉繁/冪等跳過) 都有測試
- 改轉錄相關邏輯時**不要每次都重跑模型或 API**: 先把一次的原始回傳存成 json, 之後拿那份 json 餵純邏輯函式驗證。一小時的檔跑一次 Scribe 要 $0.62、跑一次 Breeze 要 20 分鐘, 反覆重跑很浪費
- 實驗新參數時用 **5 分鐘切片**而不是整場, 迭代速度差 10 倍
- **格式的權威是 `scripts/build_pptx.py` 本身**, 不是文件。改了 parser 或版型規則, 要同步改 `references/formats.md`
- 跑過 build 之後 `examples/mini-deck/output/` 的 pptx 二進位每次都不同 (即使內容沒變), 收尾前 `git checkout -- examples/mini-deck/output/` 還原, 不要把它當成有意義的異動 commit 進去

### 已知 minor (未修, 遇到不用重查)

- `### [section]` 這一行若沒帶標題文字, `RE_PAGE` 不 match, 但拋出的錯誤訊息會指向別的原因, 誤導
- 圖片行 `![描述](路徑)` 前面有縮排就不 match (`RE_IMAGE` 綁 `^`)

### 已終結的方向 (不要重新提議)

- **第七階段 polish (送 Claude Design 美化)**: 2026-09-08 試過用 claude-design MCP 半自動化, 技術上跑得通, 但 MCP 沒有任何工具能替 app 裡的 agent 送出訊息或觸發匯出 (`put_conversation` 只是把對話複製顯示在面板, 不會執行), 手動 key prompt 這步拔不掉, 所以整個階段取消。美化由使用者自行處理
- **第八步驟 upload 到 Google Drive**: 2026-09-08 加過, 2026-09-09 使用者要求移除。要重加先重新確認需求, 不要照舊參數復原
- **逐字稿帶時間戳**: 2026-09-14 討論過, 使用者明確要純文字段落。不要「順便」加回去。(時間戳仍然要拿來**決定分段**, 只是不寫進輸出)
- **keyterms 存檔機制 (全域 terms.txt + deck 的 TERMS.md + `--prompt` 三層疊加)**: 2026-09-14 提案過, 使用者否決, 理由是不想多一套檔案格式要維護。取而代之的是「轉錄前一定要先確認專有名詞」這條流程規則 (見前面同名小節)。要重提先確認需求真的變了
- **再去比別的 STT 模型**: 2026-09-14 已經實測比過四個, 不要重跑一輪。faster-whisper `large-v3` (21.8x realtime, 但簡繁混雜、台灣口音差); `asadfgglie/faster-whisper-large-v3-zh-TW` (59x realtime 最快, 但辨識品質最差且會卡重複迴圈); Breeze-ASR-25 (本地最佳但無標點); Scribe V2 (整體最佳)。換模型換不出品質, 瓶頸是音訊本身 (語速快、中英混雜密集、會議室收音)
- **其他線上 STT 服務**: 2026-09-14 評估過, 都不如 Scribe。雅婷逐字稿 (台灣口音最準但只送 20 分鐘, 之後 100元/小時, 且是網頁無法自動化); HuggingFace Space / Colab (要手動上傳下載); fal 上的 wizper (就是 large-v3, 換到雲端不會變好, 只是多花錢)
- ⚠️ `docs/2026-09-07-deck-pipeline-design.md` 第 295 行仍寫著「新增第七階段 polish」, 那是設計當下的版本, **已作廢**, 以本文件為準
