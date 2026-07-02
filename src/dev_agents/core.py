from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

from scripts.config import READ_REPOS_ROOT, TASKS_ROOT, ensure_dirs
from scripts.llm_router import generate
from scripts.path_router import PathPolicyError, repo_path

TASK_TYPES = {
    "plan",
    "explain",
    "bugfix",
    "feature",
    "refactor",
    "test",
    "review",
    "docs",
    "commit_message",
}

SAFE_COMMANDS = {
    "npm test",
    "pnpm test",
    "pytest",
    "npm run lint",
    "pnpm lint",
    "npm run typecheck",
    "pnpm typecheck",
}

DANGEROUS_MARKERS = ["rm -rf", "sudo", "curl | sh", "ssh", "git push", "powershell", "del ", "remove-item"]
DIFF_START = re.compile(r"^(diff --git |--- |\*\*\* Begin Patch)")


def list_repos() -> list[dict]:
    ensure_dirs()
    repos = []
    for item in sorted(READ_REPOS_ROOT.iterdir()):
        if item.is_dir():
            repos.append({"name": item.name, "path": str(item), "is_git": (item / ".git").exists()})
    return repos


def get_repo(repo_name: str) -> Path:
    path = repo_path(repo_name)
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Repository not found: {repo_name}")
    return path


def get_writable_repo(repo_name: str) -> Path:
    path = repo_path(repo_name, writable=True)
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Writable repository not found: {repo_name}")
    return path


def repo_overview(repo: Path, max_files: int = 220) -> str:
    ignored = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next"}
    lines = []
    for path in sorted(repo.rglob("*")):
        rel = path.relative_to(repo)
        if any(part in ignored for part in rel.parts):
            continue
        if path.is_file():
            lines.append(str(rel))
        if len(lines) >= max_files:
            lines.append("... truncated ...")
            break
    return "\n".join(lines)


def read_relevant_files(repo: Path, limit: int = 12, max_chars: int = 20000) -> str:
    candidates = []
    names = ["README.md", "pyproject.toml", "package.json", "requirements.txt", "src", "app", "scripts"]
    for name in names:
        p = repo / name
        if p.is_file():
            candidates.append(p)
        elif p.is_dir():
            candidates.extend([x for x in sorted(p.rglob("*")) if x.is_file()][:4])
    parts = []
    used = 0
    for path in candidates[:limit]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if used + len(text) > max_chars:
            text = text[: max(0, max_chars - used)]
        used += len(text)
        parts.append(f"### FILE: {path.relative_to(repo)}\n{text}")
        if used >= max_chars:
            break
    return "\n\n".join(parts)


def task_dir(task_id: str) -> Path:
    out = TASKS_ROOT / "finished" / task_id
    out.mkdir(parents=True, exist_ok=True)
    return out


def save_task(task_id: str, payload: dict, patch: str | None = None) -> dict:
    out = task_dir(task_id)
    (out / "task.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if patch is not None:
        (out / "patch.diff").write_text(patch, encoding="utf-8")
    return {"task_id": task_id, "dir": str(out)}


def make_task_id(repo_name: str, task_type: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_repo = "".join(c if c.isalnum() or c in "-_" else "_" for c in repo_name)[:40]
    return f"{stamp}-{safe_repo}-{task_type}"


def generate_plan(repo_name: str, task_description: str, task_type: str = "plan", mode: str = "api") -> dict:
    if task_type not in TASK_TYPES:
        raise ValueError(f"Unsupported task_type: {task_type}")
    repo = get_repo(repo_name)
    overview = repo_overview(repo)
    snippets = read_relevant_files(repo)
    prompt = f"""You are a careful local repository development assistant.
Default behavior: do not write files, do not run shell, do not commit, do not push.
Answer in Chinese. Use concrete steps and testing advice.

Task type: {task_type}
Task description: {task_description}

Repository file list:
{overview}

Relevant files:
{snippets}
"""
    plan = generate(prompt, mode=mode)
    task_id = make_task_id(repo_name, task_type)
    payload = {"repo_name": repo_name, "task_type": task_type, "task_description": task_description, "plan": plan, "allow_write": False, "allow_shell": False}
    payload.update(save_task(task_id, payload))
    return payload


def generate_patch(repo_name: str, task_description: str, mode: str = "api") -> dict:
    repo = get_repo(repo_name)
    overview = repo_overview(repo)
    snippets = read_relevant_files(repo)
    prompt = f"""Generate a unified diff patch for the task below.
Do not describe changes outside the diff except for short notes after the patch.
Do not assume permission to write files. Do not include git commit or git push commands.

Task description: {task_description}

Repository file list:
{overview}

Relevant files:
{snippets}
"""
    patch = generate(prompt, mode=mode)
    task_id = make_task_id(repo_name, "patch")
    payload = {"repo_name": repo_name, "task_type": "patch", "task_description": task_description, "patch": patch, "allow_write": False, "allow_shell": False}
    payload.update(save_task(task_id, payload, patch=patch))
    return payload


def repo_diff(repo_name: str) -> dict:
    repo = get_repo(repo_name)
    return _repo_diff(repo_name, repo)


def _repo_diff(repo_name: str, repo: Path) -> dict:
    if not (repo / ".git").exists():
        raise PermissionError("Repository diff requires a git repository.")
    completed = subprocess.run(["git", "diff", "--", "."], cwd=repo, text=True, capture_output=True, timeout=60)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or "git diff failed")
    return {"repo_name": repo_name, "diff": completed.stdout[-20000:]}


def _task_payload(task_id: str) -> dict:
    task = (TASKS_ROOT / "finished" / task_id / "task.json").resolve()
    allowed = (TASKS_ROOT / "finished").resolve()
    try:
        task.relative_to(allowed)
    except ValueError as exc:
        raise PathPolicyError("task_id must resolve under tasks/finished") from exc
    if not task.exists():
        raise FileNotFoundError(f"Task not found: {task_id}")
    return json.loads(task.read_text(encoding="utf-8"))


def _patch_text(task_id: str) -> str:
    patch_path = (TASKS_ROOT / "finished" / task_id / "patch.diff").resolve()
    allowed = (TASKS_ROOT / "finished").resolve()
    try:
        patch_path.relative_to(allowed)
    except ValueError as exc:
        raise PathPolicyError("task_id must resolve under tasks/finished") from exc
    if not patch_path.exists():
        raise FileNotFoundError(f"Patch not found for task: {task_id}")
    text = patch_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if DIFF_START.match(line):
            return "\n".join(lines[idx:]).strip() + "\n"
    raise ValueError("No unified diff content found in patch task.")


def apply_patch_task(task_id: str, confirm: bool = False) -> dict:
    if not confirm:
        raise PermissionError("confirm must be true to apply a saved patch.")
    payload = _task_payload(task_id)
    repo_name = payload.get("repo_name")
    if not isinstance(repo_name, str) or not repo_name:
        raise ValueError("Saved task does not contain repo_name.")
    repo = get_writable_repo(repo_name)
    if not (repo / ".git").exists():
        raise PermissionError("Applying patches requires a git repository.")
    patch = _patch_text(task_id)
    check = subprocess.run(["git", "apply", "--check", "--whitespace=fix"], cwd=repo, input=patch, text=True, capture_output=True, timeout=60)
    if check.returncode != 0:
        return {"applied": False, "repo_name": repo_name, "task_id": task_id, "check_stdout": check.stdout[-8000:], "check_stderr": check.stderr[-8000:]}
    applied = subprocess.run(["git", "apply", "--whitespace=fix"], cwd=repo, input=patch, text=True, capture_output=True, timeout=60)
    if applied.returncode != 0:
        return {"applied": False, "repo_name": repo_name, "task_id": task_id, "stdout": applied.stdout[-8000:], "stderr": applied.stderr[-8000:]}
    return {"applied": True, "repo_name": repo_name, "task_id": task_id, "diff": _repo_diff(repo_name, repo)["diff"]}


def validate_command(command: str) -> str:
    normalized = " ".join(command.lower().strip().split())
    if any(marker in normalized for marker in DANGEROUS_MARKERS):
        raise PermissionError(f"Dangerous command rejected: {command}")
    if normalized not in SAFE_COMMANDS:
        raise PermissionError(f"Command is not whitelisted: {command}")
    return normalized


def run_safe_test(repo_name: str, command: str, allow_shell: bool = False) -> dict:
    if not allow_shell:
        raise PermissionError("allow_shell must be true to execute a whitelisted command.")
    repo = get_writable_repo(repo_name)
    normalized = validate_command(command)
    completed = subprocess.run(normalized.split(), cwd=repo, text=True, capture_output=True, timeout=120)
    return {"command": normalized, "returncode": completed.returncode, "stdout": completed.stdout[-8000:], "stderr": completed.stderr[-8000:]}
