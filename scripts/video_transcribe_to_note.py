from __future__ import annotations

from pathlib import Path
import subprocess

from faster_whisper import WhisperModel

from scripts.config import INPUT_ROOT, ensure_dirs
from scripts.extract_file import extract_to_markdown
from scripts.ingest_file import ingest_markdown
from scripts.note_file import make_note
from scripts.path_router import resolve_local_media, transcript_path

VIDEO_DIR = INPUT_ROOT / "video"


def download_audio(url: str) -> Path:
    ensure_dirs()
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    cmd = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", str(VIDEO_DIR / "%(title)s.%(ext)s"), url]
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True)
    candidates = list(VIDEO_DIR.glob("*.mp3"))
    if not candidates:
        raise RuntimeError("No mp3 file found after yt-dlp download.")
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    print(f"[OK] Audio: {latest}")
    return latest


def audio_from_url_or_file(value: str) -> Path:
    if value.startswith(("http://", "https://")):
        return download_audio(value)
    return resolve_local_media(value)


def transcribe_audio(audio_path: Path, model_size: str = "base", language: str | None = None, category: str = "default") -> Path:
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_path), language=language, vad_filter=True, beam_size=5)
    lines = [f"#### {audio_path.stem}", "", "##### Transcript", "", f"Detected language: {info.language}", ""]
    for seg in segments:
        text = seg.text.strip()
        if text:
            lines.append(f"[{round(seg.start, 2)} - {round(seg.end, 2)}] {text}")
    out = transcript_path(audio_path.name, category=category)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Transcript: {out}")
    return out


def video_transcribe_to_note(
    url_or_file: str,
    note_mode: str = "api",
    whisper_model: str = "base",
    category: str = "default",
    output_dir: str | None = None,
) -> dict:
    audio = audio_from_url_or_file(url_or_file)
    transcript = transcribe_audio(audio, model_size=whisper_model, category=category)
    md = extract_to_markdown(str(transcript), source_type="video", category=category, trusted_path=True)
    ingest = ingest_markdown(str(md), source_type="video", category=category, source=url_or_file)
    note = make_note(str(md), mode=note_mode, source_type="video", category=category, output_dir=output_dir, source=url_or_file)
    print(f"[DONE] Note: {note}")
    return {"audio": str(audio), "transcript": str(transcript), "markdown": str(md), "note": str(note), "ingest": ingest}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("url_or_file")
    parser.add_argument("--mode", default="api")
    parser.add_argument("--whisper-model", default="base")
    parser.add_argument("--category", default="default")
    parser.add_argument("--out", dest="output_dir")
    args = parser.parse_args()
    video_transcribe_to_note(args.url_or_file, note_mode=args.mode, whisper_model=args.whisper_model, category=args.category, output_dir=args.output_dir)
