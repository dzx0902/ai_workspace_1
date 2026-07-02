from __future__ import annotations

from scripts.extract_file import extract_to_markdown
from scripts.ingest_file import ingest_markdown
from scripts.note_file import make_note


def process(
    filename: str,
    note_mode: str = "api",
    source_type: str = "text",
    category: str = "default",
    output_dir: str | None = None,
) -> dict:
    md = extract_to_markdown(filename, source_type=source_type, category=category)
    ingest = ingest_markdown(str(md), source_type=source_type, category=category, source=filename)
    note = make_note(str(md), mode=note_mode, source_type=source_type, category=category, output_dir=output_dir, source=filename)
    result = {"markdown": str(md), "note": str(note), "ingest": ingest}
    print(f"[DONE] Processed: {filename}")
    print(f"[DONE] Markdown: {md}")
    print(f"[DONE] Note: {note}")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--mode", default="api")
    parser.add_argument("--source-type", default="text")
    parser.add_argument("--category", default="default")
    parser.add_argument("--out", dest="output_dir")
    args = parser.parse_args()
    process(args.file, note_mode=args.mode, source_type=args.source_type, category=args.category, output_dir=args.output_dir)
