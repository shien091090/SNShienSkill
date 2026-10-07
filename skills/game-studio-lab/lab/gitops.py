"""專案資料夾的 git 操作。push 失敗不 force, 只回傳警告字串給使用者。"""
import subprocess
from pathlib import Path

ATTRIBUTION = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"


def _git(project: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=project, capture_output=True, text=True,
                          encoding="utf-8", check=check)


class SetupError(Exception):
    pass


class Git:
    def remote_is_empty(self, repo: str) -> bool:
        r = subprocess.run(["git", "ls-remote", "--heads", repo], capture_output=True, text=True,
                           encoding="utf-8")
        if r.returncode != 0:
            raise SetupError(f"讀不到遠端 repo {repo}: {r.stderr.strip()}")
        return r.stdout.strip() == ""

    def init(self, project: Path, repo: str) -> None:
        _git(project, "init", "-b", "main")
        _git(project, "remote", "add", "origin", repo)

    def commit_push(self, project: Path, message: str) -> str | None:
        """commit 專案內全部變動並 push; 沒變動就略過。回傳警告(push 失敗原文)或 None。"""
        _git(project, "add", "-A")
        if _git(project, "status", "--short").stdout.strip() == "":
            return None
        _git(project, "commit", "-m", f"{message}\n\n{ATTRIBUTION}")
        branch = _git(project, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        r = _git(project, "push", "-u", "origin", branch, check=False)
        if r.returncode != 0:
            return f"push 失敗(commit 已留在本地): {r.stderr.strip()}"
        return None
