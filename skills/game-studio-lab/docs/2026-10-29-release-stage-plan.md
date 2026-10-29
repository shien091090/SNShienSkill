# 發布階段 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 game-studio-lab 加上發布階段: 打磨停點可選 `release`, 另有不靠進度檔的 `release` 指令給捕泡手用, 產出 `<專案>/release/{game,assets,options}`。

**Architecture:** 發布做成一張獨立的 LangGraph 子圖(`lab/release.py`): 遊戲複本 → 素材資訊 → 美術方案 → 輸出 PNG → 選擇頁 → 停在 `waiting_release_pick` → 定版。主圖把它當 `release` 節點掛在 interview 後, 定版後回 interview; 單獨指令直接編譯這張子圖, 進度檔放 `<資料夾>/.lab/release.sqlite`。PNG 輸出、選擇頁、定版、解析使用者檔都是程式(非 AI), 可測。

**Tech Stack:** Python 3 + LangGraph(既有)、pytest、Node(接合腳本)、本機 Chrome headless。

**Spec:** `docs/2026-10-29-release-stage-design.md`

## Global Constraints

- 圖示 512×512 PNG, 不放文字; 分享預覽圖 1200×630 PNG, 含遊戲名稱; 各 3 方案: 圖示 A/B/C、主色 1/2/3、預覽圖 A/B/C
- 支援裝置固定「只支援電腦」
- 單一檔案不超過 25MB(超過列入 warnings, 不擋)
- 名稱統一: 開始畫面(打磨版 / 原遊戲 + 發布複本)、預覽圖、素材資訊用同一名稱
- 不碰 PVDWebsite repo; 不改鍵名格式、不做 postMessage、不做手機
- 節點 `claude -p` 仍限縮工具; 共同守則「禁止啟動瀏覽器」對 AI 節點不變, Chrome 只由程式(render)啟動, 繪製頁不載入音效
- commit 訊息照現有 `commit_message` 風格: `[feat] [<專案資料夾名>] ...`

## Review Focus

1. 使用者檔(release-info / release-pick)欄位缺漏或代號格式錯 → CLI 當場 SetupError, 不進流程(Task 1 測)
2. 方案檔少一張或 PNG 尺寸不對 → render 節點 LabError 指出哪張(Task 2 測)
3. 選 `redo` 只重做美術方案與 PNG, 不重做遊戲複本與素材資訊(Task 3 測)
4. 發布後再打磨一輪: `polish/game/` 埋點仍在、release/ 不被打磨流程刪除(Task 3 測: remove_round_dirs 不碰 `release`)
5. 單獨指令在非空 `release/` 上重跑: 覆蓋 game/ 與 options/, assets/ 到定版才換(Task 4 測)

---

### Task 1: 發布用的純函式(解析、比例、PNG 尺寸、選擇頁、素材資訊)

**Files:**
- Create: `lab/release.py`(本 task 只放函式, 子圖在 Task 2)
- Test: `tests/test_release.py`

**Interfaces:**
- Produces:
  - `parse_release_info(text: str) -> dict` → `{"name", "code", "intro"}`; 檔案格式每行 `名稱: ...` / `代號: ...` / `介紹: ...`(全形或半形冒號皆可); 缺欄或代號不符 `^[a-z0-9]+(-[a-z0-9]+)*$` → `ValueError`(訊息中文, 指出哪欄)
  - `parse_release_pick(text: str) -> dict` → `{"icon": "A|B|C", "color": "1|2|3", "share": "A|B|C"}`; 鍵 `圖示` / `主色` / `預覽圖`; 不合法 → `ValueError`
  - `aspect_ratio(iface: dict) -> tuple[str, bool]` → 由 `canvas.width/height` 算, 例 `(1280,720)→("16:9", True)`, `(720,1280)→("9:16", False)`, `(480,640)→("3:4", False)`; 沒 canvas → `("未知", False)`
  - `png_size(path: Path) -> tuple[int, int]` 讀 IHDR
  - `write_png(path: Path, w: int, h: int, rgb=(255,255,255))` 純 zlib/struct 產單色 PNG(給假 renderer 與測試用)
  - `build_options_page(release: Path, info: dict, colors: list[dict]) -> Path` 寫 `release/options/index.html`, 回傳路徑
  - `write_asset_info(release: Path, info: dict, color: dict) -> Path` 寫 `release/assets/素材資訊.md`
  - 常數 `ICON = (512, 512)`、`SHARE = (1200, 630)`、`ICON_IDS = ("A","B","C")`、`COLOR_IDS = ("1","2","3")`、`MAX_FILE_MB = 25`、`DEVICE = "只支援電腦"`

`info` dict 的完整鍵(後續 task 共用): `name, code, intro, time, time_estimated(bool), ratio, ratio_16_9(bool), controls, device`。`colors` 每項 `{"id": "1", "bg": "#f29cac", "fg": "#2d2144", "note": "..."}`。

- [ ] **Step 1: 寫失敗測試** — `test_parse_release_info_ok`(三欄、半形與全形冒號)、`test_parse_release_info_rejects`(缺介紹、代號 `Ghost_Echo` → ValueError 且訊息含「代號」)、`test_parse_release_pick`(`圖示: b` 轉大寫 `B`;`主色: 4` → ValueError)、`test_aspect_ratio`(上述三組)、`test_png_roundtrip`(`write_png` 512×512 → `png_size == (512,512)`)、`test_options_page_lists_all`(頁面含 `圖示 A`…`C`、`主色 1`…`3`、`預覽圖 A`…`C`、三個色碼、`icon-a.png`、`share-c.png`, 不含 `<button` / `<input`)、`test_asset_info_fields`(含素材清單欄位名: 遊戲代號、遊戲名稱、遊戲介紹、遊玩時長、支援裝置、遊戲主色、遊戲畫面比例、操作方式說明; time_estimated 為 True 時時長後註「(估計)」; 主色行同時寫底色與字色)
- [ ] **Step 2: 跑 `.venv/Scripts/python -m pytest tests/test_release.py` 確認失敗**
- [ ] **Step 3: 實作上述函式** — 選擇頁: 三區塊(圖示 / 主色 / 預覽圖), 圖示區每張附 150/60/30 px 的圓角 + 粗框縮圖(`border-radius:22%; border:4px solid #2d2144`); 主色區每組畫一張仿網站卡片(主色底、fg 字色、遊戲名稱 + 時長、左側放圖示 A); 預覽圖以寬 600 顯示; 純靜態 HTML, 以相對路徑引用同資料夾 PNG
- [ ] **Step 4: 跑測試確認通過**
- [ ] **Step 5: commit** `[feat] [game-studio-lab] [發布階段] 新增發布素材的解析與輸出工具`

### Task 2: 發布子圖、Chrome renderer、假執行器、prompts

**Files:**
- Modify: `lab/release.py`(加子圖)
- Create: `lab/renderer.py`
- Modify: `lab/fake.py`, `lab/runner.py`, `lab/graph.py`(Deps 加欄位)
- Create: `prompts/release-game.md`, `prompts/release-info.md`, `prompts/release-art.md`
- Test: `tests/test_release.py`, `tests/test_prompts.py`

**Interfaces:**
- Consumes: Task 1 全部
- Produces:
  - `Deps` 加 `renderer: object = None`(`.render(html: Path, out: Path, size: tuple[int,int]) -> None`); graph 內用 `deps.renderer or ChromeRenderer()`
  - `lab/renderer.py`: `ChromeRenderer.render(...)` 用 `chrome --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --window-size=W,H --virtual-time-budget=3000 --screenshot=<out> file:///<html>`, Chrome 路徑依序找環境變數 `LAB_CHROME`、`C:/Program Files/Google/Chrome/Application/chrome.exe`、Edge; 找不到 → `RenderError("找不到 Chrome")`; 逾時 60 秒; 跑完確認輸出存在。`FakeRenderer.render` 用 `write_png` 產指定尺寸
  - `build_release_graph(deps) -> StateGraph 編譯結果`, State `ReleaseState(project, round_dir, feedback, standalone: bool, release_warnings: list)`, output 只交 `release_warnings`
  - 節點與 ctx(runner 任務名 → agent): `release-game`(game-rd)、`release-info`(一般 session, MODELS sonnet)、`release-art`(game-artist)。ctx 共通: `project, release_dir, src_dir(含 game/ 的資料夾), name, code, intro`; release-info 另加 `logs`(lab: `<project>/polish/logs`; 單獨: `<project>/telemetry.md`)
  - `src_dir`: 單獨 = `project`; 否則 `project/round_dir/game`(即 `polish/game`)
  - interrupt 值: `{"kind": "waiting_release_pick", "options_page": "<abs>/release/options/index.html"}`; resume 值 `{"choice": "pick"|"redo", "feedback": <pick 檔>}`

節點順序與行為:
1. `game`: 清空並重建 `release/game/`(複製 `src_dir/game`); `src_dir/interface.json` 存在就複製到 `release/interface.json`; 跑 `release-game`; 之後 `checker.check(release/game, "polish")`, 單獨模式以外也檢查 `src_dir/game`; 任一不過 → `LabError`(含錯誤)。`release_warnings` 重設 `[]`
2. `info`: 跑 `release-info`, 讀它寫的 `release/options/info.json`(`time, time_estimated, controls`), 合併使用者三欄 + `aspect_ratio(release/interface.json)` + `device`, 寫回同檔
3. `art`: 清掉 `options/` 下的 `icon-*`、`share-*`、`colors.json`; 跑 `release-art`; 要求 `options/icon-{a,b,c}.html`、`share-{a,b,c}.html`、`colors.json`(3 組, id 1~3)齊全, 缺 → LabError 列缺的檔
4. `render`: 每張 html → 同名 png, 尺寸以 `png_size` 驗, 不符 → LabError; 再 `build_options_page`
5. `pick`: interrupt; `redo` → `Command(goto="art")`; `pick` → 解析檔(ValueError 轉 LabError)→ 下一步
6. `finalize`: 清空 `release/assets/`, 複製 `icon-x.png → icon.png`、`share-x.png → share.png`, `write_asset_info`; 掃 `release/game` 與 `assets` 超過 25MB 的檔 → `release_warnings`

prompts(格式照現有 prompt: 「任務 / 請讀取 / 要做的事 / 回報」):
- `release-game.md`: 在 `$release_dir/game/` 移除一局結束下載試玩紀錄(下載函式、呼叫點、`gamelog-*` 相關 localStorage 鍵與補送機制), 不能下載任何檔案; 開始畫面名稱與 `$name` 不同時, **同時**改 `$release_dir/game/` 與 `$src_dir/game/` 的開始畫面名稱(可改 art.js 的標題文字, 不改圖形); `$release_dir/interface.json` 不存在時依程式寫一份(格式直接寫在 prompt 裡: `canvas{width,height}`、`draw[{name,state}]` 須含 drawTitle / drawTutorial、`sounds`、`music`); 不動其他玩法; Node 自測
- `release-info.md`: 讀試玩紀錄 `$logs` 算一局時長寫成「X–Y 分鐘」, 沒有可用紀錄就依 spec / 關卡數估並 `time_estimated: true`; 整理操作方式(一句, 例「方向鍵移動、Z 攻擊」); 只寫 `$release_dir/options/info.json` 的 `time, time_estimated, controls`
- `release-art.md`: 用 `$release_dir/game/art/art.js` 的角色與場景重新排版, 寫 3 張圖示繪製頁(512×512, 不透明背景, 不放文字, 重要內容在中間 80%)與 3 張預覽圖繪製頁(1200×630, 含遊戲名稱 `$name`); 繪製頁 `body{margin:0}`、canvas 等於頁面尺寸、以相對路徑載入 `../game/art/art.js`, **不載入 audio**; 3 組主色寫 `colors.json`(優先從 #f29cac / #aaefd5 / #4776c3 / #e0c64f 挑, 可依遊戲配色另提, 每組給 fg 深 `#2d2144` 或白 `#ffffff`, note 一句理由); 三個方案要明顯不同(構圖、主角、場景); 不得啟動瀏覽器, 用 Node vm + 假 canvas 自測不拋錯

- [ ] **Step 1: 寫失敗測試**(`tests/test_release.py`, 用 FakeRunner + FakeRenderer + NodeChecker, 單獨編譯子圖跑 `standalone=True`, 專案以 `tests/fixtures/good` 的 `game/` 當來源、不放 interface.json):
  - `test_release_pauses_with_options_page`: 停在 `waiting_release_pick`; `options_page` 存在; 9 張 png 存在且尺寸正確; `info.json` 有 name/code/intro/ratio/device
  - `test_release_pick_finalizes_assets`: resume pick(圖示 B、主色 2、預覽圖 A)→ 結束; `assets/icon.png`、`share.png`、`素材資訊.md` 存在; 素材資訊含主色 2 的色碼
  - `test_release_redo_only_reruns_art`: redo 後 `release-art` 呼叫 2 次、`release-game`/`release-info` 各 1 次
  - `test_release_missing_option_fails`: FakeRunner 參數讓 release-art 少寫 `share-c.html` → 錯誤訊息含 `share-c.html`
  - `test_render_size_mismatch_fails`: 用回傳錯尺寸的 renderer → 錯誤含檔名
  - `test_release_game_strips_nothing_else`: `release/game/game.js` 存在、來源 `game/` 未被刪
  - `test_chrome_renderer_real`(找不到 Chrome 就 `pytest.skip`): 渲染 200×100 純色頁 → `png_size == (200,100)`
  - `tests/test_prompts.py` 既有渲染檢查自動涵蓋新 prompt(確認無未替換的 `$變數`)
- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作 renderer、子圖、FakeRunner 的 `_release_game`(複製後在 game.js 尾加 `// release`, 無 interface.json 時複製 fixture 的)/ `_release_info` / `_release_art`(產 6 張最小繪製頁 + colors.json; 建構參數 `drop_option: str|None` 供缺檔測試)、runner 的 AGENTS / MODELS**
- [ ] **Step 4: 跑全部測試確認通過**
- [ ] **Step 5: commit** `[feat] [game-studio-lab] [發布階段] 新增發布流程與方案輸出`

### Task 3: 掛進主流程(打磨選 release)

**Files:**
- Modify: `lab/graph.py`, `lab/state.py`, `lab/cli.py`
- Test: `tests/test_graph.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `build_release_graph`、`parse_release_info`、`parse_release_pick`
- Produces: `FEEDBACK_CHOICES["polish"]` 加 `release`; `PICK_CHOICES = {"pick", "redo"}`; `LabState` 加 `release_warnings`; 狀態 JSON 新增 `status: "waiting_release_pick"` 帶 `options_page` 與 `allowed_choices`

- [ ] **Step 1: 寫失敗測試**
  - graph: `test_polish_release_then_back_to_interview` — 打磨停點 resume `choice=release, feedback=<info 檔>` → 停在 waiting_release_pick → resume pick → 回到 waiting_feedback(round 不變、`review` 沒被呼叫、`polish/game/` 仍在、`release/assets/icon.png` 存在)→ 再 continue 一輪打磨後 `release/` 仍在
  - cli: `test_release_choice_validation` — 非打磨階段選 release → error; info 缺介紹 → error 訊息含「介紹」; 停在 pick 時選 continue → error; pick 檔不合法 → error
  - cli: `test_release_commits` — release 後遠端最新 commit 為 `[feat] [proj] 產出發布用遊戲與素材方案`; pick 後為 `[feat] [proj] 發布素材定版`; redo 為 `[feat] [proj] 重做發布素材方案`; status JSON 有 `options_page`
- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作** — interview 的 `choice == "release"` → `Command(goto="release")`; 主圖 `add_node("release", release_graph)` + `add_edge("release", "interview")`; `report()` 處理新 kind; `cmd_resume` 依 kind 驗證(release / pick 先用 parse 函式驗檔, ValueError 轉 SetupError); `run()` 在 choice 為 pick 時把 `release_warnings` 併入 warnings; `commit_message` 加上述三種訊息; `remove_round_dirs` 的正規式本就不含 release, 測試鎖住即可
- [ ] **Step 4: 跑全部測試確認通過**
- [ ] **Step 5: commit** `[feat] [game-studio-lab] [發布階段] 打磨停點新增發布選項`

### Task 4: 單獨的 release 指令(捕泡手)

**Files:**
- Modify: `lab/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `python -m lab release <資料夾> --info <檔>`(開始或重做整個發布) / `python -m lab release <資料夾> --choice pick|redo [--feedback <pick 檔>]`(停在挑選頁時); 進度檔 `<資料夾>/.lab/release.sqlite`, thread_id `release`; `<資料夾>` 必須是 git repo 且有 `game/index.html`, 否則 SetupError; 若 `<資料夾>/.lab/checkpoint.sqlite` 存在(是 lab 專案)→ SetupError 請改用 resume --choice release

- [ ] **Step 1: 寫失敗測試** — `test_standalone_release_flow`(tmp 建 git repo + bare 遠端、複製 fixture `game/`; release --info → waiting_release_pick 且遠端 commit `[feat] [<資料夾名>] 產出發布用遊戲與素材方案`; --choice pick → done, `release/assets/` 齊; 再 release --info → 又停在挑選頁, 舊 `assets/` 仍在直到 pick)、`test_standalone_rejects_lab_project`、`test_standalone_requires_game`
- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作 `cmd_release`**(重用 `run` 的 commit/push 邏輯, 抽出共用小函式; 停在挑選頁又給 --info → SetupError「請先 pick 或 redo」; 流程中途出錯停下時不帶參數 `release <資料夾>` 從失敗節點接續)
- [ ] **Step 4: 跑全部測試確認通過**
- [ ] **Step 5: commit** `[feat] [game-studio-lab] [發布階段] 新增不靠進度檔的發布指令`

### Task 5: SKILL.md 與參考文件

**Files:**
- Modify: `SKILL.md`
- Create: `references/release-guide.md`

- [ ] **Step 1: SKILL.md** — 指令表加 `release`; 打磨的 choice 表加 `release`; 新增「發布」段: 問名稱 / 介紹 / 代號(代號預設依序: 上次 `release/assets/素材資訊.md` → `E:\Project\PVDWebsite\site\js\games.js` 的 code → 由專案名推, 給使用者確認; 介紹 30–60 字, 超出提醒不代改)、寫 `polish/release-info.md`(單獨指令寫在 `<資料夾>/release-info.md`)、背景執行、停在 `waiting_release_pick` 時給選擇頁路徑、收代號寫 `release-pick.md` 再 pick / redo; 定版後回報 `release/` 路徑與 warnings; 名稱統一的說明; 捕泡手走單獨指令
- [ ] **Step 2: `references/release-guide.md`** — 兩個使用者檔的格式範例
- [ ] **Step 3: 跑 `.venv/Scripts/python -m pytest` 全過**
- [ ] **Step 4: commit** `[docs] [game-studio-lab] [發布階段] 說明發布階段的操作流程`
