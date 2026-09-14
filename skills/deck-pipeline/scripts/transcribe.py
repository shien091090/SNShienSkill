"""把 deck 資料夾裡的語音檔轉成同名 .md 逐字稿。

線上: ElevenLabs Scribe V2 (fal), 品質好但要錢; 本地: Breeze-ASR-25, 免費但品質明顯差。
走哪條由使用者決定, 不指定引擎會直接報錯 (見 main)。

用法:
    py -3.12-64 transcribe.py <deck> --scan
    py -3.12-64 transcribe.py <deck> --scribe [--prompt 通行證,排行賽]
    py -3.12-64 transcribe.py <deck> --local  [--prompt 通行證,排行賽] [--cpu]
"""
from __future__ import annotations

import argparse
import datetime
import math
import re
import sys
from pathlib import Path
from typing import Callable, Iterable, Sequence

MODEL_ID = "MediaTek-Research/Breeze-ASR-25"

# 線上主力: ElevenLabs Scribe V2 (透過 fal)
SCRIBE_ENDPOINT = "fal-ai/elevenlabs/speech-to-text/scribe-v2"
SCRIBE_MODEL_NAME = "ElevenLabs Scribe V2 (fal) + OpenCC s2tw"
SCRIBE_RATE_PER_MIN = 0.008      # USD
SCRIBE_KEYTERM_PREMIUM = 1.3     # 用 keyterms 加價 30%
SCRIBE_API_MAX_SEC = 1200        # API 硬限制, 超過回 422 audio_duration_too_long
SCRIBE_CHUNK_SEC = 900           # 實際切檔長度, 留餘裕

AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"}
SKIP_DIRS = {"output"}
SENTENCE_END = "。？！?!"
PUNCTUATION = "。，、！？；：,.!?;:「」『』()（）"
PROMPT_BASE = "以下是台灣中文的會議錄音逐字稿，請用繁體中文轉寫。"
# 模型偶爾會把 prompt 直接複述出來, 這些片段在輸出裡一律當雜訊清掉
PROMPT_ECHO_FRAGMENTS = (PROMPT_BASE, "以下是台灣中文的會議錄音逐字稿", "請用繁體中文轉寫")
MIN_PARAGRAPH_CHARS = 200
MAX_PARAGRAPH_CHARS = 400  # 段落字數硬上限, 保底用; Breeze 沒標點沒停頓時只剩這條
PAUSE_GAP = 1.0          # 秒; 停頓超過這個長度就換段。Scribe 的 word 級時間戳有真實
                         # 停頓 (一小時 108 次 >= 1 秒); whisper 長檔時間戳連續, 幾乎不觸發
MIN_PAUSE_CHARS = 100    # 段落短於這個字數時不因停頓換段, 免得切出一堆碎段
TARGET_RATE = 16000

# 連續重複 4 次以上的 2~40 字單元 = 幻覺迴圈。單字重複 (笑聲之類) 不碰。
RE_REPEAT = re.compile(r"(.{2,40}?)\1{3,}", re.DOTALL)

# segment = (文字, 起秒, 迄秒); 沒有時間戳時後兩者為 None
Segment = tuple


# ---------------------------------------------------------------- 掃檔

def find_audio_files(deck: Path) -> list[Path]:
    """遞迴找出 deck 底下所有語音檔, 依相對路徑排序; 跳過 output/。"""
    deck = Path(deck)
    found = [
        p
        for p in deck.rglob("*")
        if p.is_file()
        and p.suffix.lower() in AUDIO_EXTS
        and not SKIP_DIRS & set(p.relative_to(deck).parts[:-1])
    ]
    return sorted(found, key=lambda p: p.relative_to(deck).as_posix())


def transcript_path(audio: Path) -> Path:
    """逐字稿永遠是音檔的同層同名 .md。"""
    return Path(audio).with_suffix(".md")


def needs_transcript(audio: Path) -> bool:
    return not transcript_path(audio).exists()


# ---------------------------------------------------------------- 併段

def merge_segments(
    segments: Iterable[Segment],
    min_chars: int = MIN_PARAGRAPH_CHARS,
    pause_gap: float = PAUSE_GAP,
    min_pause_chars: int = MIN_PAUSE_CHARS,
    max_chars: int = MAX_PARAGRAPH_CHARS,
) -> list[str]:
    """把碎 segment 併成段落。

    三種換段條件, 由弱到強:
    1. 累積超過 min_chars 且剛好停在句末標點 — 有標點時才用得到
    2. 講者停頓超過 pause_gap 秒 (且當前段落已達 min_pause_chars) — 真實的段落邊界,
       但 whisper 的長檔時間戳是連續的, 一小時大概只會觸發十幾次
    3. 超過 max_chars 就在 segment 邊界硬換 — 保證段落可讀。Breeze 不吐標點,
       沒有這條的話整份會是一面文字牆 (實測一小時講座最長一段 4622 字)
    """
    paragraphs: list[str] = []
    current = ""
    prev_end: float | None = None

    def flush() -> None:
        nonlocal current
        if current.strip():
            paragraphs.append(current.strip())
        current = ""

    for text, start, end in segments:
        # 不能 strip 每個 chunk: word 級 segment 把空格掛在尾巴, 拿掉英文會黏成一團
        chunk = text or ""
        if not chunk.strip():
            continue
        settled = current.strip()
        long_pause = (
            settled
            and prev_end is not None
            and start is not None
            and start - prev_end >= pause_gap
            and len(settled) >= min_pause_chars
        )
        if long_pause or (settled and len(settled) + len(chunk.strip()) > max_chars):
            flush()
        current += chunk
        prev_end = end
        settled = current.strip()
        if len(settled) >= min_chars and settled[-1] in SENTENCE_END:
            flush()
    flush()
    return paragraphs


def collapse_repeats(text: str) -> str:
    """把幻覺重複迴圈壓成一次。

    模型碰到非語音段 (影片配樂、長靜音) 會卡在重複同一短語數十次。
    """
    return RE_REPEAT.sub(lambda m: m.group(1), text)


# ---------------------------------------------------------------- 逐字稿內容

def build_initial_prompt(terms: Sequence[str]) -> str:
    """initial_prompt 只用來餵專有名詞; 繁體由模型本身保證。"""
    if not terms:
        return PROMPT_BASE
    return PROMPT_BASE + "可能出現的專有名詞：" + "、".join(terms) + "。"


def _depunct(text: str) -> str:
    return "".join(c for c in text if c not in PUNCTUATION and not c.isspace())


def strip_prompt_echo(segments: Iterable[Segment]) -> list[Segment]:
    """清掉「把 initial_prompt 複述出來」的部分, 時間戳保留。

    整段就是複述 → 整段丟掉; 複述混在真實內容裡 → 只把複述那截拿掉。
    只比對固定的 PROMPT_BASE, 不比對專有名詞 — 那些詞本來就會真的出現在錄音裡。
    """
    base = _depunct(PROMPT_BASE)
    out: list[Segment] = []
    for text, start, end in segments:
        chunk = text or ""
        if _depunct(chunk) in base:
            continue
        for fragment in PROMPT_ECHO_FRAGMENTS:
            chunk = chunk.replace(fragment, "")
        if chunk.strip():
            out.append((chunk, start, end))
    return out


def render_transcript(
    *, audio_name: str, model_name: str, date: str, paragraphs: Sequence[str]
) -> str:
    head = (
        "---\n"
        f"轉自: {audio_name}\n"
        f"模型: {model_name}\n"
        f"轉錄日期: {date}\n"
        "---\n"
    )
    body = "".join(f"\n{p}\n" for p in paragraphs)
    return head + body


# ---------------------------------------------------------------- 轉錄流程

def transcribe_deck(
    deck: Path,
    *,
    make_transcriber: Callable[[], Callable[[Path, str], list[str]]],
    today: str,
    model_name: str = MODEL_ID,
    terms: Sequence[str] | None = None,
    post_process: Callable[[str], str] | None = None,
    log: Callable[[str], None] | None = None,
) -> list[Path]:
    """轉錄所有還沒有逐字稿的語音檔, 回傳寫出的 .md 路徑。

    全部都有逐字稿時完全不載入模型 (make_transcriber 不會被呼叫)。
    """
    deck = Path(deck)
    say = log or (lambda _msg: None)
    pending = [a for a in find_audio_files(deck) if needs_transcript(a)]
    if not pending:
        say("沒有需要轉錄的語音檔")
        return []

    prompt = build_initial_prompt(list(terms or []))
    transcriber = make_transcriber()
    written: list[Path] = []
    for audio in pending:
        say(f"轉錄 {audio.relative_to(deck).as_posix()} ...")
        paragraphs = [collapse_repeats(p) for p in merge_segments(transcriber(audio, prompt))]
        if post_process:
            paragraphs = [post_process(p) for p in paragraphs]
        out = transcript_path(audio)
        out.write_text(
            render_transcript(
                audio_name=audio.name,
                model_name=model_name,
                date=today,
                paragraphs=paragraphs,
            ),
            encoding="utf-8",
        )
        written.append(out)
        say(f"  -> {out.relative_to(deck).as_posix()}")
    return written


# ---------------------------------------------------------------- scan 報表

def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    total = int(round(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def scan_rows(
    deck: Path, probe: Callable[[Path], float | None]
) -> list[tuple[str, float | None, bool]]:
    deck = Path(deck)
    rows = []
    for audio in find_audio_files(deck):
        rows.append(
            (
                audio.relative_to(deck).as_posix(),
                probe(audio),
                not needs_transcript(audio),
            )
        )
    return rows


def format_scan_table(rows: Sequence[tuple[str, float | None, bool]]) -> str:
    lines = ["| 檔案 | 長度 | 逐字稿 |", "|---|---|---|"]
    for name, seconds, has in rows:
        mark = "有" if has else "缺"
        lines.append(f"| {name} | {format_duration(seconds)} | {mark} |")
    total = sum(s for _, s, _ in rows if s)
    missing = sum(1 for _, _, has in rows if not has)
    lines.append("")
    lines.append(f"共 {len(rows)} 個語音檔, 總長 {format_duration(total)}, {missing} 個缺逐字稿")
    return "\n".join(lines)


# ---------------------------------------------------------------- Scribe 用的純邏輯

def estimate_scribe_cost(seconds: float, with_keyterms: bool = True) -> float:
    """Scribe V2 的花費估算 (USD)。不足一分鐘算一分鐘, 估貴不估便宜。"""
    minutes = math.ceil(seconds / 60)
    cost = minutes * SCRIBE_RATE_PER_MIN
    return cost * SCRIBE_KEYTERM_PREMIUM if with_keyterms else cost


def format_cost_estimate(seconds: float, with_keyterms: bool = True) -> str:
    cost = estimate_scribe_cost(seconds, with_keyterms)
    note = " (含 keyterms 加價 30%)" if with_keyterms else ""
    return "總長 %s, 走 Scribe V2 估計花費 US$%.2f%s" % (format_duration(seconds), cost, note)


def split_plan(total_seconds: float, max_sec: int = SCRIBE_CHUNK_SEC) -> list[tuple[int, float, float]]:
    """回傳 [(第幾段, 起秒, 長度), ...]; Scribe 有 1200 秒上限, 長檔一定要切。"""
    if max_sec > SCRIBE_API_MAX_SEC:
        raise ValueError(f"每段不得超過 {SCRIBE_API_MAX_SEC} 秒 (Scribe API 上限), 給的是 {max_sec}")
    plan = []
    index = 0
    start = 0.0
    while start < total_seconds:
        index += 1
        plan.append((index, start, min(float(max_sec), total_seconds - start)))
        start += max_sec
    return plan


def words_to_segments(words: Iterable[dict], offset: float = 0.0) -> list[Segment]:
    """Scribe 的 word 物件轉成 segment; spacing 併進前一段, audio_event 保留。"""
    out: list[Segment] = []
    for word in words:
        text = word.get("text", "")
        if word.get("type") == "spacing":
            if out:
                prev_text, prev_start, prev_end = out[-1]
                out[-1] = (prev_text + text, prev_start, prev_end)
            continue
        start, end = word.get("start"), word.get("end")
        out.append((
            text,
            None if start is None else start + offset,
            None if end is None else end + offset,
        ))
    return out


def to_traditional_tw(text: str) -> str:
    """簡轉繁 (台灣用字)。

    用 s2tw 不用 s2twp — s2twp 的慣用詞轉換會把「文本」改成「文字」, 在遊戲業是錯的。
    OpenCC 一律產出「臺」, 但台灣慣用「台」, 所以最後再換一次。
    """
    from opencc import OpenCC

    return OpenCC("s2tw").convert(text).replace("臺", "台")


def repair_mojibake(text: str) -> str:
    """修 UTF-8 被當 Latin-1 讀出來的亂碼; 正常文字原樣回傳。"""
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


# ---------------------------------------------------------------- 解碼 (av)

def decode_audio(path: Path):
    """用 PyAV 解成 16kHz 單聲道 float32; 不需要系統安裝 ffmpeg。"""
    import av
    import numpy as np

    resampler = av.audio.resampler.AudioResampler(format="flt", layout="mono", rate=TARGET_RATE)
    chunks = []
    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().reshape(-1))
        for out in resampler.resample(None):
            chunks.append(out.to_ndarray().reshape(-1))
    if not chunks:
        return np.zeros(0, dtype="float32"), TARGET_RATE
    return np.concatenate(chunks).astype("float32"), TARGET_RATE


def probe_duration(path: Path) -> float | None:
    try:
        import av
    except ImportError:
        return None
    try:
        with av.open(str(path)) as container:
            if container.duration:
                return container.duration / av.time_base
            stream = container.streams.audio[0]
            if stream.duration and stream.time_base:
                return float(stream.duration * stream.time_base)
    except Exception:
        return None
    return None


# ---------------------------------------------------------------- Scribe backend (fal)

FAL_RUN = Path.home() / ".claude" / "skills" / "fal-generate" / "fal_run.ps1"


def _call_fal_scribe(wav: Path, terms: Sequence[str], workdir: Path) -> dict:
    """送一段 wav 給 fal Scribe V2, 回傳 raw response dict。"""
    import json
    import subprocess

    payload = {
        "audio_url": "__INPUT_FILE_URL__",
        "language_code": "zho",
        "tag_audio_events": True,
        "diarize": False,
        "keyterms": list(terms)[:100],
    }
    payload_file = workdir / (wav.stem + "_payload.json")
    payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result_file = workdir / (wav.stem + "_result.txt")

    # 輸出走檔案不走 stdout pipe: 直接 capture stdout 會讓中文被當 Latin-1 讀成亂碼
    script = (
        "$env:FAL_KEY=[Environment]::GetEnvironmentVariable('FAL_KEY','User'); "
        f"& '{FAL_RUN}' -Endpoint '{SCRIBE_ENDPOINT}' -PayloadFile '{payload_file}' "
        f"-InputFile '{wav}' -OutDir '{workdir}' -Category stt -TimeoutSec 1800 "
        f"| Out-File -FilePath '{result_file}' -Encoding utf8"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=False)

    if not result_file.exists():
        raise RuntimeError(f"fal_run.ps1 沒有產生輸出: {wav.name}")
    lines = [l for l in result_file.read_text(encoding="utf-8").splitlines() if l.startswith("{")]
    if not lines:
        raise RuntimeError(f"fal 沒有回傳 JSON: {result_file}")
    res = json.loads(lines[-1])
    if res.get("status") != "ok":
        raise RuntimeError(f"fal 失敗: {json.dumps(res, ensure_ascii=False)[:400]}")
    return res.get("raw") or {}


def make_scribe_transcriber(
    terms: Sequence[str] = (), log: Callable[[str], None] = print
) -> Callable[[Path, str], list[Segment]]:
    """線上轉錄。需要 FAL_KEY (User scope) 與 fal-generate 的 fal_run.ps1。

    Scribe 有 1200 秒上限, 所以長檔一定要切; 每段的時間戳再補上偏移合回去。
    這一層沒有被 pytest 蓋到 (會真的花錢), 改動後要跑一次真實 smoke test。
    """
    import tempfile
    import wave

    import numpy as np

    def run(audio_path: Path, _initial_prompt: str) -> list[Segment]:
        samples, rate = decode_audio(audio_path)
        total = len(samples) / rate
        plan = split_plan(total)
        log(f"  切成 {len(plan)} 段送 Scribe (每段上限 {SCRIBE_CHUNK_SEC}s)")
        segments: list[Segment] = []
        with tempfile.TemporaryDirectory(prefix="scribe_") as tmp:
            workdir = Path(tmp)
            for index, start, duration in plan:
                part = samples[int(start * rate) : int((start + duration) * rate)]
                wav = workdir / ("part%02d.wav" % index)
                pcm = (np.clip(part, -1, 1) * 32767).astype("<i2")
                with wave.open(str(wav), "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(rate)
                    w.writeframes(pcm.tobytes())
                log(f"  第 {index}/{len(plan)} 段 ({format_duration(duration)}) ...")
                raw = _call_fal_scribe(wav, terms, workdir)
                words = [
                    {**word, "text": repair_mojibake(word.get("text", ""))}
                    for word in (raw.get("words") or [])
                ]
                segments.extend(words_to_segments(words, offset=start))
        return segments

    return run


# ---------------------------------------------------------------- Breeze backend

def make_breeze_transcriber(force_cpu: bool = False, log: Callable[[str], None] = print):
    """回傳一個 (audio_path, initial_prompt) -> list[str] 的轉錄函式。

    這一層沒有被 pytest 蓋到 (要載 4GB 模型), 改動後要跑一次真實 smoke test。
    """
    import torch
    from transformers import pipeline

    use_cuda = torch.cuda.is_available() and not force_cpu
    if use_cuda:
        log(f"使用 GPU: {torch.cuda.get_device_name(0)}")
    else:
        log("使用 CPU 轉錄, 會很慢 (一小時錄音可能要跑數十分鐘)")

    # 不要傳 chunk_length_s: transformers v5 判斷的是 is not None, 傳 0 反而會進實驗性
    # 分塊路徑; 不傳才會走 whisper 自己的 sequential long-form, 長檔也吃得下。
    asr = pipeline(
        "automatic-speech-recognition",
        model=MODEL_ID,
        dtype=torch.bfloat16 if use_cuda else torch.float32,
        device=0 if use_cuda else -1,
    )
    # BPE tokenizer 的 clean_up 會吃掉標點前的空格, 中英混雜逐字稿會被弄壞。
    asr.tokenizer.clean_up_tokenization_spaces = False

    def run(audio_path: Path, initial_prompt: str) -> list[str]:
        samples, rate = decode_audio(audio_path)
        generate_kwargs = {"language": "zh", "task": "transcribe"}
        if initial_prompt:
            try:
                prompt_ids = asr.tokenizer.get_prompt_ids(initial_prompt, return_tensors="pt")
                generate_kwargs["prompt_ids"] = prompt_ids.to(asr.model.device)
            except Exception as exc:  # noqa: BLE001
                log(f"  initial_prompt 套用失敗, 改用無提示轉錄: {exc}")
        result = asr(
            {"array": samples, "sampling_rate": rate},
            return_timestamps=True,
            generate_kwargs=generate_kwargs,
        )
        chunks = result.get("chunks") or []
        if chunks:
            segments = []
            for c in chunks:
                start, end = (c.get("timestamp") or (None, None))[:2]
                segments.append((c.get("text", ""), start, end))
        else:
            segments = [(result.get("text", ""), None, None)]
        return strip_prompt_echo(segments)

    return run


# ---------------------------------------------------------------- CLI

def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="把 deck 裡的語音檔轉成同名 .md 逐字稿")
    parser.add_argument("deck", type=Path)
    parser.add_argument("--scan", action="store_true", help="只列出語音檔、時長與 Scribe 花費估算")
    parser.add_argument("--scribe", action="store_true", help="線上轉錄 (ElevenLabs Scribe V2, 要錢)")
    parser.add_argument("--local", action="store_true", help="本地轉錄 (Breeze, 免費但品質差)")
    parser.add_argument("--prompt", default="", help="專有名詞, 逗號分隔")
    parser.add_argument("--cpu", action="store_true", help="--local 時強制用 CPU")
    args = parser.parse_args(argv)

    deck: Path = args.deck
    if not deck.is_dir():
        print(f"資料夾不存在: {deck}", file=sys.stderr)
        return 1

    terms = [t.strip() for t in args.prompt.split(",") if t.strip()]

    if args.scan:
        rows = scan_rows(deck, probe_duration)
        if not rows:
            print("沒有找到語音檔")
            return 0
        print(format_scan_table(rows))
        pending = sum(s for _, s, has in rows if s and not has)
        if pending:
            print(format_cost_estimate(pending, with_keyterms=bool(terms)))
        return 0

    if args.scribe == args.local:
        print(
            "要指定轉錄引擎: --scribe (線上, 要錢) 或 --local (本地 Breeze, 免費)。\n"
            "先跑 --scan 看花費估算, 並讓使用者決定走哪條, 不要自己選。",
            file=sys.stderr,
        )
        return 2

    if args.scribe:
        written = transcribe_deck(
            deck,
            make_transcriber=lambda: make_scribe_transcriber(terms=terms),
            today=datetime.date.today().isoformat(),
            model_name=SCRIBE_MODEL_NAME,
            terms=terms,
            post_process=to_traditional_tw,
            log=print,
        )
    else:
        written = transcribe_deck(
            deck,
            make_transcriber=lambda: make_breeze_transcriber(force_cpu=args.cpu),
            today=datetime.date.today().isoformat(),
            terms=terms,
            log=print,
        )
    print(f"完成, 寫出 {len(written)} 份逐字稿")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
