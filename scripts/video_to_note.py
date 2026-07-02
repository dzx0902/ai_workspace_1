from __future__ import annotations

from pathlib import Path
import subprocess

from scripts.config import INPUT_ROOT, ensure_dirs
from scripts.extract_file import extract_to_markdown
from scripts.ingest_file import ingest_markdown
from scripts.note_file import make_note

VIDEO_INBOX = INPUT_ROOT / "video"


def download_subtitles(url: str) -> Path:
    ensure_dirs()
    VIDEO_INBOX.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "--write-subs",
        "--write-auto-subs",
        "--skip-download",
        "--sub-langs",
        "zh-Hans,zh,en",
        "--sub-format",
        "vtt/srt/best",
        "-o",
        str(VIDEO_INBOX / "%(title)s.%(ext)s"),
        url,
    ]
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True)
    candidates = list(VIDEO_INBOX.glob("*.vtt")) + list(VIDEO_INBOX.glob("*.srt"))
    if not candidates:
        raise RuntimeError("No subtitle file found. This video may not have subtitles.")
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    print(f"[OK] Subtitle: {latest}")
    return latest


def video_to_note(url: str, mode: str = "api", category: str = "default", output_dir: str | None = None) -> dict:
    sub = download_subtitles(url)
    md = extract_to_markdown(str(sub), source_type="video", category=category, trusted_path=True)
    ingest = ingest_markdown(str(md), source_type="video", category=category, source=url)
    note = make_note(str(md), mode=mode, source_type="video", category=category, output_dir=output_dir, source=url)
    print(f"[DONE] Video note: {note}")
    return {"subtitle": str(sub), "markdown": str(md), "note": str(note), "ingest": ingest}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--mode", default="api")
    parser.add_argument("--category", default="default")
    parser.add_argument("--out", dest="output_dir")
    args = parser.parse_args()
    video_to_note(args.url, mode=args.mode, category=args.category, output_dir=args.output_dir)
