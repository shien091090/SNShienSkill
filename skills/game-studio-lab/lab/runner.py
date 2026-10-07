"""AI 節點的執行器: 依任務種類組 prompt, 起一個無頭 claude -p 去做。

權限一律用限縮的工具清單, 不用 bypassPermissions。
"""
import datetime
import json
import os
import subprocess
from pathlib import Path
from string import Template

SKILL_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = SKILL_DIR / "prompts"
STUDIO_REFS = Path.home() / ".claude" / "skills" / "game-studio" / "references"

TIMEOUT_SEC = int(os.environ.get("LAB_CLAUDE_TIMEOUT", "2400"))

BASE_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep",
              "Bash(node:*)", "Bash(ls:*)", "Bash(mkdir:*)", "Bash(cp:*)"]

# 任務種類 → 沿用的 game-studio agent; 沒列的(design / triage / review)用一般 session
AGENTS = {
    "art": "game-artist", "art-fix": "game-artist",
    "rd": "game-rd", "rd-fix": "game-rd", "bugfix": "game-rd",
    "audio": "game-audio", "audio-fix": "game-audio",
}

# 沒有 agent 的任務明確指定模型, 不吃 CLI 預設(預設可能被 managed settings 改掉)。
# 有 agent 的任務用 agent 定義檔 frontmatter 的 model(美術 / 音效 opus、RD sonnet)
MODELS = {"design": "opus", "review": "opus", "triage": "sonnet"}

_AUDIO_TOOLS = ["WebSearch", "WebFetch", "Bash(curl:*)", "Bash(ffmpeg:*)", "Bash(ffprobe:*)"]
EXTRA_TOOLS = {"audio": _AUDIO_TOOLS, "audio-fix": _AUDIO_TOOLS}


class ClaudeError(Exception):
    pass


def prompt_file(kind: str, stage: str) -> Path:
    staged = PROMPTS_DIR / f"{kind}-{stage}.md"
    return staged if staged.exists() else PROMPTS_DIR / f"{kind}.md"


def render_prompt(kind: str, ctx: dict) -> str:
    values = {k: str(v) for k, v in ctx.items()}
    values.setdefault("studio_refs", str(STUDIO_REFS))
    common = (PROMPTS_DIR / "_common.md").read_text(encoding="utf-8")
    body = prompt_file(kind, ctx.get("stage", "")).read_text(encoding="utf-8")
    return Template(common + "\n\n" + body).safe_substitute(values)


def claude_cmd(kind: str) -> list[str]:
    cmd = ["claude", "-p", "--output-format", "json", "--permission-mode", "acceptEdits",
           "--add-dir", str(STUDIO_REFS),
           "--allowedTools", *BASE_TOOLS, *EXTRA_TOOLS.get(kind, [])]
    if kind in AGENTS:
        cmd += ["--agent", AGENTS[kind]]
    if kind in MODELS:
        cmd += ["--model", MODELS[kind]]
    return cmd


def probe_models(cwd: Path) -> dict:
    """每種任務用跟正式執行相同的參數起一次極短的 session, 回報實際用到的模型。"""
    out = {}
    for kind in ("design", "triage", "review", "art", "rd", "audio"):
        r = subprocess.run(claude_cmd(kind), input="只回覆 OK 兩個字, 不要做任何其他事。", cwd=cwd,
                           capture_output=True, text=True, encoding="utf-8", timeout=300)
        try:
            data = json.loads(r.stdout)
            out[kind] = sorted((data.get("modelUsage") or {}).keys()) or data.get("model") or "?"
        except json.JSONDecodeError:
            out[kind] = f"失敗(exit {r.returncode}): {r.stderr.strip()[-300:]}"
    return out


class ClaudeRunner:
    def run(self, kind: str, ctx: dict) -> str:
        project = Path(ctx["project"])
        prompt = render_prompt(kind, ctx)
        cmd = claude_cmd(kind)
        logs = project / ".lab" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        tag = "-".join(x for x in (kind, ctx.get("round_dir"), ctx.get("game")) if x)
        log_path = logs / f"{stamp}-{tag}.json"
        try:
            r = subprocess.run(cmd, input=prompt, cwd=project, capture_output=True, text=True,
                               encoding="utf-8", timeout=TIMEOUT_SEC)
        except subprocess.TimeoutExpired as e:
            raise ClaudeError(f"{tag} 逾時({TIMEOUT_SEC} 秒)") from e
        log_path.write_text(json.dumps({"cmd": cmd, "prompt": prompt, "returncode": r.returncode,
                                        "stdout": r.stdout, "stderr": r.stderr},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
        if r.returncode != 0:
            raise ClaudeError(f"{tag} 失敗(exit {r.returncode}), 紀錄在 {log_path}: {r.stderr.strip()[-800:]}")
        try:
            out = json.loads(r.stdout)
        except json.JSONDecodeError:
            return r.stdout
        if out.get("is_error"):
            raise ClaudeError(f"{tag} 回報錯誤, 紀錄在 {log_path}: {str(out.get('result'))[-800:]}")
        return str(out.get("result", ""))
