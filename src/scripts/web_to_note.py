from __future__ import annotations

from pathlib import Path

import requests
import trafilatura

from scripts.config import ensure_dirs
from scripts.ingest_file import ingest_markdown
from scripts.note_file import make_note
from scripts.path_router import processed_markdown_path, sanitize_filename


def web_to_markdown(url: str, category: str = "default") -> Path:
    ensure_dirs()
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    html = resp.text
    extracted = trafilatura.extract(html, output_format="markdown", include_tables=True, include_comments=False)
    if not extracted:
        extracted = trafilatura.extract(html, include_tables=True)
    if not extracted:
        raise RuntimeError("Failed to extract article text from URL.")
    meta = trafilatura.extract_metadata(html)
    title = meta.title if meta and meta.title else "web_article"
    out = processed_markdown_path(sanitize_filename(title), source_type="web", category=category)
    out.write_text(f"#### {title}\n\n##### Source\n- url: {url}\n\n---\n\n{extracted}\n", encoding="utf-8")
    print(f"[OK] Web extracted to {out}")
    return out


def web_to_note(url: str, mode: str = "api", category: str = "default", output_dir: str | None = None) -> dict:
    md = web_to_markdown(url, category=category)
    ingest = ingest_markdown(str(md), source_type="web", category=category, source=url)
    note = make_note(str(md), mode=mode, source_type="web", category=category, output_dir=output_dir, source=url)
    print(f"[DONE] Web note: {note}")
    return {"markdown": str(md), "note": str(note), "ingest": ingest}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--mode", default="api")
    parser.add_argument("--category", default="default")
    parser.add_argument("--out", dest="output_dir")
    args = parser.parse_args()
    web_to_note(args.url, mode=args.mode, category=args.category, output_dir=args.output_dir)
