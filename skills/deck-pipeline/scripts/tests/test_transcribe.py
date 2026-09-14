import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import transcribe as tr  # noqa: E402


def _touch(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _segs(*items):
    """把 (文字, 起, 迄) 或純文字 (無時間戳) 組成 segment list。"""
    out = []
    for it in items:
        out.append(it if isinstance(it, tuple) else (it, None, None))
    return out


# ---- 掃檔 ----

def test_find_audio_files_recurses_and_skips_output(tmp_path):
    _touch(tmp_path / "訪談.mp3")
    _touch(tmp_path / "01_背景" / "週會.m4a")
    _touch(tmp_path / "output" / "成品.wav")
    _touch(tmp_path / "01_背景" / "圖.png")

    found = tr.find_audio_files(tmp_path)

    assert [p.name for p in found] == ["週會.m4a", "訪談.mp3"]


def test_find_audio_files_is_case_insensitive(tmp_path):
    _touch(tmp_path / "錄音.MP3")

    assert [p.name for p in tr.find_audio_files(tmp_path)] == ["錄音.MP3"]


def test_transcript_path_is_sibling_md(tmp_path):
    audio = tmp_path / "01_背景" / "週會錄音.m4a"

    assert tr.transcript_path(audio) == tmp_path / "01_背景" / "週會錄音.md"


def test_needs_transcript_false_when_md_exists(tmp_path):
    audio = _touch(tmp_path / "週會.m4a")
    assert tr.needs_transcript(audio) is True

    _touch(tmp_path / "週會.md")
    assert tr.needs_transcript(audio) is False


# ---- 併段: 停頓 ----

def test_merge_segments_breaks_on_long_pause():
    segs = _segs(("甲" * 80, 0.0, 8.0), ("乙" * 80, 11.0, 19.0))

    paras = tr.merge_segments(segs, pause_gap=2.0, min_pause_chars=50)

    assert paras == ["甲" * 80, "乙" * 80]


def test_merge_segments_does_not_break_on_short_pause():
    segs = _segs(("甲" * 80, 0.0, 8.0), ("乙" * 80, 8.5, 16.0))

    paras = tr.merge_segments(segs, pause_gap=2.0, min_pause_chars=50)

    assert paras == ["甲" * 80 + "乙" * 80]


def test_merge_segments_ignores_pause_when_paragraph_still_short():
    """停頓夠長但當前段落太短就不換, 免得切出一堆碎段。"""
    segs = _segs(("好的", 0.0, 1.0), ("甲" * 80, 30.0, 38.0))

    paras = tr.merge_segments(segs, pause_gap=2.0, min_pause_chars=50)

    assert paras == ["好的" + "甲" * 80]


def test_merge_segments_without_timestamps_never_breaks_on_pause():
    segs = _segs("甲" * 80, "乙" * 80)

    paras = tr.merge_segments(segs, pause_gap=2.0, min_pause_chars=50)

    assert paras == ["甲" * 80 + "乙" * 80]


# ---- 併段: 標點 ----

def test_merge_segments_breaks_after_min_chars_at_sentence_end():
    segs = _segs("甲" * 120 + "。", "乙" * 120 + "。", "丙丁。")

    paras = tr.merge_segments(segs, min_chars=200)

    assert paras == ["甲" * 120 + "。" + "乙" * 120 + "。", "丙丁。"]


def test_merge_segments_does_not_break_mid_sentence():
    segs = _segs("甲" * 150, "乙" * 150, "丙。")

    paras = tr.merge_segments(segs, min_chars=200)

    assert paras == ["甲" * 150 + "乙" * 150 + "丙。"]


def test_merge_segments_flushes_trailing_text_without_punctuation():
    segs = _segs("甲" * 250 + "。", "結尾沒有句號")

    paras = tr.merge_segments(segs, min_chars=200)

    assert paras == ["甲" * 250 + "。", "結尾沒有句號"]


def test_merge_segments_strips_whitespace_around_segments():
    paras = tr.merge_segments(_segs("  前面。 ", "\n後面。\n"), min_chars=1)

    assert paras == ["前面。", "後面。"]


def test_merge_segments_ignores_empty_segments():
    assert tr.merge_segments(_segs("", "   ", "有字。"), min_chars=1) == ["有字。"]


# ---- 重複迴圈 ----

def test_collapse_repeats_squashes_hallucination_loop():
    assert tr.collapse_repeats("SIGONO：" * 30) == "SIGONO："


def test_collapse_repeats_keeps_surrounding_text():
    text = "點他們的預告片" + "SIGONO：" * 20 + "它就是一個這樣的東西"

    assert tr.collapse_repeats(text) == "點他們的預告片SIGONO：它就是一個這樣的東西"


def test_collapse_repeats_leaves_three_repeats_alone():
    assert tr.collapse_repeats("對啊對啊對啊") == "對啊對啊對啊"


def test_collapse_repeats_leaves_normal_text_alone():
    text = "這次我們先講背景上一版是手動撈的"

    assert tr.collapse_repeats(text) == text


def test_collapse_repeats_ignores_single_char_runs():
    """單字重複 (笑聲之類) 不碰, 只壓兩字以上的重複單元。"""
    assert tr.collapse_repeats("哈哈哈哈哈") == "哈哈哈哈哈"


# ---- prompt 洩漏 ----

def test_strip_prompt_echo_drops_segment_that_is_only_prompt():
    segs = _segs(tr.PROMPT_BASE, "真正的內容。")

    assert [t for t, _, _ in tr.strip_prompt_echo(segs)] == ["真正的內容。"]


def test_strip_prompt_echo_drops_partial_tail_of_base():
    segs = _segs("請用繁體中文轉寫", "真正的內容。")

    assert [t for t, _, _ in tr.strip_prompt_echo(segs)] == ["真正的內容。"]


def test_strip_prompt_echo_removes_inline_echo_but_keeps_speech():
    segs = _segs("請用繁體中文轉寫：它就是一個這樣的東西")

    assert [t for t, _, _ in tr.strip_prompt_echo(segs)] == ["：它就是一個這樣的東西"]


def test_strip_prompt_echo_keeps_domain_terms_from_prompt():
    segs = _segs("通行證。", "排行賽的獎勵。")

    assert [t for t, _, _ in tr.strip_prompt_echo(segs)] == ["通行證。", "排行賽的獎勵。"]


def test_strip_prompt_echo_keeps_normal_speech():
    segs = _segs("這次我們先講背景。", "上一版是手動撈的。")

    assert [t for t, _, _ in tr.strip_prompt_echo(segs)] == [
        "這次我們先講背景。",
        "上一版是手動撈的。",
    ]


def test_strip_prompt_echo_preserves_timestamps():
    segs = _segs(("真正的內容。", 3.0, 9.0))

    assert tr.strip_prompt_echo(segs) == [("真正的內容。", 3.0, 9.0)]


def test_strip_prompt_echo_can_return_empty():
    assert tr.strip_prompt_echo(_segs(tr.PROMPT_BASE)) == []


# ---- 逐字稿內容 ----

def test_render_transcript_has_frontmatter_and_paragraphs():
    text = tr.render_transcript(
        audio_name="週會錄音.m4a",
        model_name="MediaTek-Research/Breeze-ASR-25",
        date="2026-09-14",
        paragraphs=["第一段。", "第二段。"],
    )

    assert text == (
        "---\n"
        "轉自: 週會錄音.m4a\n"
        "模型: MediaTek-Research/Breeze-ASR-25\n"
        "轉錄日期: 2026-09-14\n"
        "---\n"
        "\n"
        "第一段。\n"
        "\n"
        "第二段。\n"
    )


def test_build_initial_prompt_includes_terms():
    prompt = tr.build_initial_prompt(["通行證", "排行賽"])

    assert "通行證" in prompt and "排行賽" in prompt


def test_build_initial_prompt_without_terms_is_plain_zh_tw():
    prompt = tr.build_initial_prompt([])

    assert "繁體中文" in prompt
    assert "、" not in prompt


# ---- 轉錄流程 ----

class FakeFactory:
    def __init__(self, segments):
        self.segments = segments
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return lambda path, initial_prompt: list(self.segments)


def test_transcribe_deck_writes_transcript_and_loads_model_once(tmp_path):
    _touch(tmp_path / "訪談.mp3")
    _touch(tmp_path / "01_背景" / "週會.m4a")
    factory = FakeFactory(_segs("這是內容。"))

    written = tr.transcribe_deck(tmp_path, make_transcriber=factory, today="2026-09-14")

    assert factory.calls == 1
    assert [p.name for p in written] == ["週會.md", "訪談.md"]
    body = (tmp_path / "訪談.md").read_text(encoding="utf-8")
    assert "轉自: 訪談.mp3" in body
    assert "這是內容。" in body


def test_transcribe_deck_collapses_repeats_before_writing(tmp_path):
    _touch(tmp_path / "週會.m4a")
    factory = FakeFactory(_segs("開頭" + "SIGONO：" * 20 + "結尾"))

    tr.transcribe_deck(tmp_path, make_transcriber=factory, today="2026-09-14")

    body = (tmp_path / "週會.md").read_text(encoding="utf-8")
    assert "開頭SIGONO：結尾" in body


def test_transcribe_deck_skips_existing_transcripts(tmp_path):
    _touch(tmp_path / "週會.m4a")
    _touch(tmp_path / "週會.md", "我手改過的逐字稿")
    factory = FakeFactory(_segs("不該被寫進去。"))

    written = tr.transcribe_deck(tmp_path, make_transcriber=factory, today="2026-09-14")

    assert written == []
    assert factory.calls == 0
    assert (tmp_path / "週會.md").read_text(encoding="utf-8") == "我手改過的逐字稿"


def test_transcribe_deck_passes_initial_prompt_with_terms(tmp_path):
    _touch(tmp_path / "週會.m4a")
    seen = {}

    def factory():
        def run(path, initial_prompt):
            seen["prompt"] = initial_prompt
            return _segs("內容。")
        return run

    tr.transcribe_deck(tmp_path, make_transcriber=factory, today="2026-09-14", terms=["通行證"])

    assert "通行證" in seen["prompt"]


# ---- scan 報表 ----

def test_format_duration_renders_minutes_and_seconds():
    assert tr.format_duration(754) == "12:34"
    assert tr.format_duration(None) == "?"


def test_format_scan_table_marks_missing_transcripts():
    table = tr.format_scan_table([("訪談.mp3", 754, False), ("01_背景/週會.m4a", 60, True)])

    assert "| 訪談.mp3 | 12:34 | 缺 |" in table
    assert "| 01_背景/週會.m4a | 01:00 | 有 |" in table


def test_scan_rows_reports_relative_paths_and_transcript_state(tmp_path):
    _touch(tmp_path / "01_背景" / "週會.m4a")
    _touch(tmp_path / "01_背景" / "週會.md")
    _touch(tmp_path / "訪談.mp3")

    rows = tr.scan_rows(tmp_path, probe=lambda p: 60.0)

    assert rows == [("01_背景/週會.m4a", 60.0, True), ("訪談.mp3", 60.0, False)]


# ---- 解碼 (需要 av) ----

def test_decode_audio_returns_mono_16k(tmp_path):
    pytest.importorskip("av")
    import math
    import wave

    src = tmp_path / "tone.wav"
    with wave.open(str(src), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        frames = bytearray()
        for i in range(44100):
            v = int(12000 * math.sin(i * 0.05))
            frames += v.to_bytes(2, "little", signed=True) * 2
        w.writeframes(bytes(frames))

    samples, rate = tr.decode_audio(src)

    assert rate == 16000
    assert samples.ndim == 1
    assert 15000 < len(samples) < 17000
    assert str(samples.dtype) == "float32"


def test_probe_duration_reads_seconds(tmp_path):
    pytest.importorskip("av")
    import wave

    src = tmp_path / "silence.wav"
    with wave.open(str(src), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000 * 3)

    assert 2.5 < tr.probe_duration(src) < 3.5


# ---- 併段: 字數硬上限 ----

def test_merge_segments_breaks_at_max_chars_on_segment_boundary():
    segs = _segs("甲" * 30, "乙" * 30, "丙" * 30)

    paras = tr.merge_segments(segs, max_chars=50)

    assert paras == ["甲" * 30, "乙" * 30, "丙" * 30]


def test_merge_segments_packs_segments_up_to_max_chars():
    segs = _segs("甲" * 20, "乙" * 20, "丙" * 20)

    paras = tr.merge_segments(segs, max_chars=50)

    assert paras == ["甲" * 20 + "乙" * 20, "丙" * 20]


def test_merge_segments_never_splits_a_single_long_segment():
    segs = _segs("甲" * 120)

    assert tr.merge_segments(segs, max_chars=50) == ["甲" * 120]


# ---- 花費估算 ----

def test_estimate_scribe_cost_uses_per_minute_rate():
    # 60 分鐘 * $0.008, 不加 keyterms
    assert tr.estimate_scribe_cost(3600, with_keyterms=False) == pytest.approx(0.48)


def test_estimate_scribe_cost_adds_keyterm_premium():
    assert tr.estimate_scribe_cost(3600, with_keyterms=True) == pytest.approx(0.624)


def test_estimate_scribe_cost_rounds_partial_minutes_up():
    """不足一分鐘也算一分鐘, 估貴不估便宜。"""
    assert tr.estimate_scribe_cost(61, with_keyterms=False) == pytest.approx(0.016)


def test_format_cost_estimate_reports_duration_and_price():
    msg = tr.format_cost_estimate(3600, with_keyterms=True)

    assert "60:00" in msg
    assert "0.62" in msg


# ---- 切檔計畫 ----

def test_split_plan_splits_into_chunks_under_limit():
    plan = tr.split_plan(3593.6, max_sec=900)

    assert [p[0] for p in plan] == [1, 2, 3, 4]
    assert [p[1] for p in plan] == [0.0, 900.0, 1800.0, 2700.0]
    assert plan[-1][2] == pytest.approx(893.6)


def test_split_plan_keeps_short_audio_as_one_chunk():
    plan = tr.split_plan(300.0, max_sec=900)

    assert plan == [(1, 0.0, 300.0)]


def test_split_plan_rejects_max_over_api_limit():
    with pytest.raises(ValueError):
        tr.split_plan(100.0, max_sec=1500)


# ---- Scribe word 物件轉 segment ----

def test_words_to_segments_keeps_timestamps():
    words = [
        {"text": "你", "start": 1.0, "end": 1.2, "type": "word"},
        {"text": "好", "start": 1.2, "end": 1.4, "type": "word"},
    ]

    assert tr.words_to_segments(words) == [("你", 1.0, 1.2), ("好", 1.2, 1.4)]


def test_words_to_segments_attaches_spacing_to_previous():
    words = [
        {"text": "用", "start": 1.0, "end": 1.2, "type": "word"},
        {"text": " ", "start": None, "end": None, "type": "spacing"},
        {"text": "Unity", "start": 1.3, "end": 1.9, "type": "word"},
    ]

    assert tr.words_to_segments(words) == [("用 ", 1.0, 1.2), ("Unity", 1.3, 1.9)]


def test_words_to_segments_keeps_audio_events():
    words = [{"text": "[笑]", "start": 2.0, "end": 2.5, "type": "audio_event"}]

    assert tr.words_to_segments(words) == [("[笑]", 2.0, 2.5)]


def test_words_to_segments_offsets_by_chunk_start():
    words = [{"text": "你", "start": 1.0, "end": 1.2, "type": "word"}]

    assert tr.words_to_segments(words, offset=900.0) == [("你", 901.0, 901.2)]


# ---- 簡轉繁 ----

def test_to_traditional_tw_converts_simplified():
    assert tr.to_traditional_tw("这个游戏的关卡逻辑") == "這個遊戲的關卡邏輯"


def test_to_traditional_tw_uses_tai_not_tai_formal():
    """台灣慣用「台」不是「臺」。"""
    assert tr.to_traditional_tw("台北电玩展") == "台北電玩展"


def test_to_traditional_tw_keeps_domain_wording():
    """不要用 s2twp 的慣用詞轉換, 那會把「文本」改成「文字」。"""
    assert "文本" in tr.to_traditional_tw("游戏文本很重要")


def test_to_traditional_tw_is_idempotent_on_traditional():
    assert tr.to_traditional_tw("這個遊戲的關卡邏輯") == "這個遊戲的關卡邏輯"


# ---- mojibake 修復 ----

def test_repair_mojibake_restores_utf8_read_as_latin1():
    broken = "很難".encode("utf-8").decode("latin-1")

    assert tr.repair_mojibake(broken) == "很難"


def test_repair_mojibake_leaves_correct_text_alone():
    assert tr.repair_mojibake("很難") == "很難"


def test_repair_mojibake_leaves_ascii_alone():
    assert tr.repair_mojibake("hello world") == "hello world"


def test_transcribe_deck_applies_post_process_to_paragraphs(tmp_path):
    _touch(tmp_path / "週會.m4a")
    factory = FakeFactory(_segs("这个游戏"))

    tr.transcribe_deck(
        tmp_path,
        make_transcriber=factory,
        today="2026-09-14",
        post_process=tr.to_traditional_tw,
    )

    body = (tmp_path / "週會.md").read_text(encoding="utf-8")
    assert "這個遊戲" in body


def test_transcribe_deck_without_post_process_leaves_text_alone(tmp_path):
    _touch(tmp_path / "週會.m4a")
    factory = FakeFactory(_segs("这个游戏"))

    tr.transcribe_deck(tmp_path, make_transcriber=factory, today="2026-09-14")

    assert "这个游戏" in (tmp_path / "週會.md").read_text(encoding="utf-8")


def test_merge_segments_preserves_spaces_between_english_words():
    """word 級 segment 會把空格掛在前一段尾巴, 不能被 strip 掉, 否則英文會黏成一團。"""
    segs = _segs("用 ", "Indie ", "Prize ", "做例子")

    assert tr.merge_segments(segs) == ["用 Indie Prize 做例子"]


def test_merge_segments_still_trims_paragraph_edges():
    assert tr.merge_segments(_segs("  前面 ", "後面  "), min_chars=1) == ["前面 後面"]
