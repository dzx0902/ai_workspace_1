from __future__ import annotations

import re
from pathlib import Path

from scripts import config

_VALID_SEGMENT = re.compile(r"^[^\0]+$")


class PathPolicyError(ValueError):
    pass


def _resolve(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def assert_under(path: Path | str, roots: list[Path], label: str) -> Path:
    resolved = _resolve(path)
    root_list = [_resolve(root) for root in roots]
    if not any(is_relative_to(resolved, root) for root in root_list):
        allowed = ", ".join(str(root) for root in root_list)
        raise PathPolicyError(f"{label} is outside allowed roots: {resolved}. Allowed roots: {allowed}")
    return resolved


def safe_relative_path(value: str | None) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    raw = str(value).replace("\\", "/").strip().strip("/")
    candidate = Path(raw)
    if candidate.is_absolute():
        raise PathPolicyError("Absolute paths are not accepted here; use a relative path.")
    parts = candidate.parts
    if any(part in ("", ".", "..") for part in parts):
        raise PathPolicyError(f"Path traversal is not allowed: {value}")
    if any(not _VALID_SEGMENT.match(part) for part in parts):
        raise PathPolicyError(f"Invalid path segment in: {value}")
    return candidate


def safe_slug(value: str, fallback: str = "default") -> str:
    text = str(value or "").strip().replace("\\", "/").strip("/")
    if not text or text in (".", "..") or ".." in Path(text).parts:
        return fallback
    return text


def note_output_dir(source_type: str, category: str = "default", output_dir: str | None = None) -> Path:
    config.ensure_dirs()
    if output_dir:
        rel = safe_relative_path(output_dir)
        assert rel is not None
        out = (config.OBSIDIAN_VAULT / rel).resolve()
    else:
        rel = Path("AI") / safe_slug(source_type) / safe_slug(category)
        out = (config.OBSIDIAN_VAULT / rel).resolve()
    out = assert_under(out, [config.OBSIDIAN_VAULT, config.NOTES_ROOT], "Note output directory")
    out.mkdir(parents=True, exist_ok=True)
    return out


def processed_markdown_path(name: str, source_type: str, category: str = "default") -> Path:
    config.ensure_dirs()
    stem = sanitize_filename(Path(name).stem or "document")
    out_dir = config.PROCESSED_MD / safe_slug(source_type) / safe_slug(category)
    out_dir.mkdir(parents=True, exist_ok=True)
    return assert_under(out_dir / f"{stem}.md", [config.PROCESSED_MD], "Processed markdown path")


def transcript_path(name: str, category: str = "default") -> Path:
    config.ensure_dirs()
    stem = sanitize_filename(Path(name).stem or "transcript")
    out_dir = config.PROCESSED_TRANSCRIPTS / safe_slug(category)
    out_dir.mkdir(parents=True, exist_ok=True)
    return assert_under(out_dir / f"{stem}.md", [config.PROCESSED_TRANSCRIPTS], "Transcript path")


def resolve_input_file(filename: str, source_type: str | None = None) -> Path:
    raw = str(filename).strip()
    if not raw:
        raise PathPolicyError("filename is required")
    path = Path(raw).expanduser()
    if path.is_absolute():
        candidates = [path]
    else:
        roots = [config.UPLOADS_ROOT]
        if source_type:
            roots.append(config.INPUT_ROOT / safe_slug(source_type))
        roots.append(config.INPUT_ROOT)
        candidates = [root / path for root in roots]

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists():
            return assert_under(resolved, [config.INPUT_ROOT, config.UPLOADS_ROOT], "Input file")
    attempted = ", ".join(str(c.resolve()) for c in candidates)
    raise FileNotFoundError(f"Input file not found in allowed roots: {filename}. Tried: {attempted}")


def resolve_local_media(value: str) -> Path:
    return resolve_input_file(value, source_type="video")


def repo_path(repo_name: str, *, writable: bool = False) -> Path:
    rel = safe_relative_path(repo_name)
    if rel is None:
        raise PathPolicyError("repo_name must be a relative directory path")
    root = config.WRITE_REPOS_ROOT if writable else config.READ_REPOS_ROOT
    path = (root / rel).resolve()
    label = "Writable repository" if writable else "Repository"
    return assert_under(path, [root], label)


def sanitize_filename(value: str, fallback: str = "document") -> str:
    keep = []
    for char in value:
        if char.isalnum() or char in (" ", "-", "_", ".", "(", ")"):
            keep.append(char)
    name = "".join(keep).strip().replace(" ", "_")[:100]
    return name or fallback
