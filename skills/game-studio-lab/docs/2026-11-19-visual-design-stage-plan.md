# 視覺設計階段 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 深掘選 next 後、打磨第一輪前, 插入只跑一次的視覺設計子圖(列清單 → 確認 → 出方案 → 挑選 → 寫方向)。

> 實作時改動: 視覺設計不包成子圖, 改成主圖節點 `visual_list` → `visual_confirm` → `visual_art` → `visual_page` → `visual_pick`(`add_visual_nodes(g, deps, done)`)。同一個子圖裡有兩個停點時, 中途當掉後接續會把上一個停點的回答錯配給下一個停點(接續測試抓到)。

**Architecture:** 仿發布子圖: `lab/visual.py` 放純函式(解析、組方案頁、寫方向), `lab/visual_graph.py` 放子圖, 掛在主圖 review 與 design 之間; CLI 多兩個停點的回報與檢查; 兩份新 prompt + 修改打磨設計 / 美術 prompt。

**Tech Stack:** Python 3, LangGraph, pytest; 方案是瀏覽器 Canvas 2D JS。

**Spec:** `docs/2026-11-19-visual-design-stage-design.md`

## Global Constraints

- 每個專案只跑一次: `visual/direction.md` 存在就不再進視覺設計
- 只有從深掘 review 後 new_stage == polish 時進視覺設計; 打磨停點選項不變
- 每個元素 3 個方案, 代號 A/B/C; 元素代號英文小寫(`^[a-z][a-z0-9-]*$`)
- 美術節點每個元素一次 `claude -p`, 依序跑, 完成標記 `visual/options/.done-<代號>`
- 方案頁是單一 HTML(內嵌底版 `art.js` 與所有方案), 動態方案有播放 / 暫停鍵與進度條, 預設停在 t=0
- 所有使用者看得到的字用繁體中文

## Review Focus

- 方案程式執行時丟錯: 方案頁該格顯示錯誤訊息, 其他格照常(page 測試檢查有 try/catch 包住 draw)
- pick.md 漏列元素或寫了不存在的方案代號: CLI 擋下並說是哪個(test_visual)
- redo 只列部分元素: 只刪那些的方案與完成標記, 其他保留(test_graph)
- 中途當掉接續: 已完成元素不重出方案(test_graph 用 fail_once)
- 退回深掘後再 next: 不再進視覺設計(test_graph)

---

### Task 1: 解析與輸出純函式 `lab/visual.py`

**Files:**
- Create: `lab/visual.py`
- Test: `tests/test_visual.py`

**Interfaces — Produces:**
- `OPTION_IDS = ("A", "B", "C")`
- `parse_elements(text: str) -> dict` → `{"base": "deepen-2/game-b", "elements": [{"code","name","kind"("static"|"anim"),"content","why"}]}`; 缺底版、沒有元素、某節缺類型 / 內容、代號不合格、類型不是 靜態/動態 → `ValueError`(訊息點名哪一節缺什麼)
- `parse_visual_pick(text: str, codes: list[str], redo: bool = False) -> dict[str, dict]` → `{code: {"id": "A"|"B"|"C"|"", "note": str}}`; 每行 `代號: 方案[, 附註]`(全形冒號、逗號也收); pick 時每個 code 都要有、id 必為 A/B/C; redo 時至少一行、id 可省(只寫附註)、不在 codes 的代號擋下
- `missing_options(options_dir: Path, codes: list[str]) -> list[str]` → 缺的檔名(`<code>-<id>.js`、`<code>.md`)
- `build_visual_page(visual_dir: Path, elements: list[dict], art_js: Path) -> Path` → 寫出 `visual/options/index.html`
- `write_direction(visual_dir: Path, parsed: dict, picks: dict) -> Path` → 寫出 `visual/direction.md`

`elements.md` 格式:
```
底版: deepen-2/game-b

## title — 開始畫面
類型: 動態
內容: ...
為什麼是核心: ...
```

- [ ] **Step 1: 寫失敗測試** `test_parse_elements_ok`(底版、兩節、kind 轉成 anim/static)、`test_parse_elements_rejects`(參數化: 無底版 / 無元素 / 缺類型 / 代號 `Title` / 類型「會動」, 訊息含節名或欄位名)、`test_parse_pick_ok`(含附註與全形冒號)、`test_parse_pick_rejects`(漏元素 → 訊息含代號; 方案 D; 未知代號)、`test_parse_pick_redo_subset`(只列一個、只寫附註)、`test_build_page`(輸出含 art.js 內容、每個方案檔內容、`<code>` 標題、`播放`、`try` 包 draw、說明檔文字)、`test_write_direction`(含每元素選中方案代號、說明、附註、方案檔相對路徑 `options/title-B.js`)
- [ ] **Step 2: 跑 `.venv/Scripts/python -m pytest tests/test_visual.py -q`, 預期 ImportError 失敗**
- [ ] **Step 3: 實作 `lab/visual.py`**; 方案頁: 每個方案以 `<script>` 內嵌原檔後接 `__OPTS.push(window.VISUAL_OPTION)`, 頁面 JS 依 `kind` 畫靜態或建立播放控制(requestAnimationFrame, t 依實際經過秒數, loop 時 `t % duration`, 非 loop 播完停在最後一幀); 每格 `try{draw}catch(e){畫錯誤文字}`; 畫布 `width:100%` 等比縮放; 頁面樣式比照 `lab/release.py` 的選擇頁(淺底、卡片)
- [ ] **Step 4: 測試通過**
- [ ] **Step 5: (不單獨 commit, 全部完成後一起 commit)**

### Task 2: 視覺設計子圖 `lab/visual_graph.py` + 掛進主圖 + 假執行器

**Files:**
- Create: `lab/visual_graph.py`
- Modify: `lab/graph.py`(review 後路由、掛子圖、design 傳底版)、`lab/state.py`(LabState 加 `visual_base: str`)、`lab/fake.py`(`_design` 處理 stage visual、新增 `_visual_art`)、`lab/runner.py`(AGENTS 加 `"visual-art": "game-artist"`)
- Test: `tests/test_graph.py`

**Interfaces:**
- Consumes: Task 1 全部
- Produces: `build_visual_graph(deps) -> CompiledGraph`; 子圖節點 `list`(runner `design`, ctx stage=`visual`)、`confirm`(interrupt `{"kind":"waiting_visual_list","elements": <path>}`)、`art`(依序對每個元素 runner `visual-art`)、`page`、`pick`(interrupt `{"kind":"waiting_visual_pick","options_page": <path>}`; redo → 刪指定元素的方案與標記, 把附註寫進 `visual/options/<code>-redo.md`, goto art)、`direction`; 輸出 `{"visual_base": str}`
- runner ctx: list 用 `{"project","stage":"visual","round_dir": <深掘最後一輪資料夾>,"visual_dir"}`; art 用 `{"project","stage":"visual","visual_dir","base_dir": <專案>/<底版>,"element","element_name","element_kind","element_content","element_why","redo_note"(無則「無」)}`
- 主圖: `after_review` 在 choice 為 next 且舊 stage 為 deepen、`visual/direction.md` 不存在時 → `"visual"`; `visual` → `design`
- design(打磨)ctx 加 `visual_base`(沒有就「無」)

- [ ] **Step 1: 改 `test_full_path_explore_deepen_polish_end`**: deepen next 後 `interrupt_of(snap)["kind"] == "waiting_visual_list"`; resume `choice="confirm"` → `waiting_visual_pick`, `count(runner,"visual-art") == 2`; 寫 pick.md(`title: A` / `hero: B, 再胖一點`)resume `choice="pick", feedback=...` → `waiting_feedback` polish; `visual/direction.md` 含 `再胖一點`; 其餘原斷言保留(資料夾清單改為 `["archive", "polish", "visual"]`)
- [ ] **Step 2: 新增測試** `test_visual_redo_only_listed`(redo `hero: 換方向` → visual-art 共 3 次, `title-A.js` 未被重寫(mtime 不變), `hero-redo.md` 含「換方向」)、`test_visual_resume_skips_done`(fail_once `("visual-art", None)` 第二個元素… 用 runner 參數讓第 2 次 visual-art 拋錯 → 接續後 visual-art 總共 3 次)、`test_visual_runs_once`(打磨 back-deepen 再 next → 直接 waiting_feedback polish, visual-art 次數不變)
- [ ] **Step 3: 跑測試確認失敗**
- [ ] **Step 4: 實作**; 假執行器 `_design` stage visual: 寫 `visual/elements.md`(底版 = ctx round_dir 下第一款, 元素 title 動態 / hero 靜態); `_visual_art`: 寫三個方案檔(`window.VISUAL_OPTION={element,id,kind,size:[320,180],duration:2,loop:true,draw(ctx,t){ctx.fillRect(0,0,10+t*10,10)}}`)與說明檔。FakeRunner 加參數 `fail_nth: dict[kind,int]`(第 n 次呼叫該 kind 時拋錯一次)以支援接續測試
- [ ] **Step 5: 全部測試通過 `.venv/Scripts/python -m pytest -q`**

### Task 3: CLI 停點

**Files:**
- Modify: `lab/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:** Consumes Task 1 解析函式、Task 2 interrupt kinds。
- `report`: `waiting_visual_list` → `out["elements"]`, `allowed_choices ["confirm"]`; `waiting_visual_pick` → `out["options_page"]`, `["pick","redo"]`
- `cmd_resume`: list 停點只收 confirm, 用 `parse_elements` 驗 `visual/elements.md`; pick 停點: pick/redo 需 `--feedback`, 用 `parse_visual_pick(…, codes, redo=choice=="redo")` 驗
- `commit_message`: status `waiting_visual_list` → 加項「視覺設計列出核心視覺元素」; choice confirm → `[feat] [<專案>] 視覺設計產出方案`; redo(在視覺停點)→ `[feat] [<專案>] 視覺設計重做方案`; pick(在視覺停點)且進了打磨 → 項目「視覺設計定案方向」+ 原本的打磨產出項。視覺停點與發布停點都用 pick / redo, 用 `before` 狀態的停點種類區分: `run()` 先記下 resume 前的 interrupt kind 傳給 `commit_message(..., stop_kind=)`

- [ ] **Step 1: 寫失敗測試** `test_visual_stops_cli`(LAB_FAKE_CLAUDE 環境走到 deepen next → status `waiting_visual_list` 有 elements; confirm → `waiting_visual_pick` 有 options_page; pick 檔漏元素 → code 1 錯誤含元素代號; 正確 pick → `waiting_feedback`)與 `test_visual_commit_messages`(直接呼叫 commit_message 驗三種訊息)
- [ ] **Step 2: 確認失敗; Step 3: 實作; Step 4: `pytest -q` 全過**

### Task 4: Prompts 與文件

**Files:**
- Create: `prompts/design-visual.md`、`prompts/visual-art.md`
- Modify: `prompts/design-polish.md`(底版: `$visual_base` 不是「無」就用它, 不自己挑; 有 `$project/visual/direction.md` 照方向寫規格並列「視覺方向對照」)、`prompts/art.md`(打磨: 有方向檔時挑中方案程式是起點, 搬進 art.js 改成遊戲函式)、`SKILL.md`(新增「視覺設計」段、停點表)、`tests/test_prompts.py`(CTX 加 visual 變數, KINDS 加 `("design","visual")`、`("visual-art","visual")`)
- [ ] **Step 1: test_prompts 加 kinds 與變數 → 失敗; Step 2: 寫 prompt → 通過**
- [ ] **Step 3: SKILL.md 段落**: 停點①主 session 把底版與清單用白話列給使用者, 依回覆直接改 `visual/elements.md`, `resume --choice confirm`; 停點②用 Artifact 發布 `options_page`(單檔), 回覆寫成 `visual/pick.md`, `--choice pick|redo --feedback visual/pick.md`; redo 後同檔路徑重發
- [ ] **Step 4: 全部測試、skill-audit、commit + push**
