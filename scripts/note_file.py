from __future__ import annotations

from datetime import datetime
from pathlib import Path

from scripts.config import ensure_dirs
from scripts.llm_router import generate
from scripts.path_router import note_output_dir, sanitize_filename


def split_text(text: str, max_chars: int = 12000) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def summarize_chunk(chunk: str, idx: int, total: int, mode: str) -> str:
    prompt = f"""Summarize part {idx}/{total} of a long learning material.
Answer in Chinese. Keep important English technical terms. Do not invent facts.
Use concise bullets and only Markdown headings #### and ##### if headings are needed.

Content:
{chunk}
"""
    return generate(prompt, mode=mode)


def make_note(
    markdown_file: str,
    mode: str = "api",
    source_type: str = "text",
    category: str = "default",
    output_dir: str | None = None,
    source: str | None = None,
) -> Path:
    ensure_dirs()
    path = Path(markdown_file).expanduser().resolve()
    text = path.read_text(encoding="utf-8", errors="ignore")
    chunks = split_text(text)
    if len(chunks) == 1:
        material = chunks[0]
    else:
        partials = []
        for i, chunk in enumerate(chunks, start=1):
            print(f"[INFO] Summarizing chunk {i}/{len(chunks)}")
            partials.append(summarize_chunk(chunk, i, len(chunks), mode=mode))
        material = "\n\n---\n\n".join(partials)

    prompt = f"""Turn the material below into a high-quality Obsidian study note.
Answer in Chinese. Preserve important English technical terms.
Use only Markdown headings #### and #####. Do not use #, ##, or ### headings.
Do not invent information not present in the source material.

Required structure:

#### Title

##### Source
- File:
- Generated at:

##### One-sentence summary

##### Core content

##### Key concepts

##### Methods / process / mechanism

##### Important details

##### Review questions

##### Next steps

Source: {source or path}
Generated at: {datetime.now().isoformat(timespec="seconds")}

Material:
{material}
"""
    note = generate(prompt, mode=mode)
    out_dir = note_output_dir(source_type=source_type, category=category, output_dir=output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{sanitize_filename(path.stem)}.md"
    frontmatter = f"""---
source_file: "{path}"
source: "{source or path}"
source_type: "{source_type}"
category: "{category}"
generated_at: "{datetime.now().isoformat(timespec='seconds')}"
pipeline: "ai_workspace_api"
---

"""
    out.write_text(frontmatter + note, encoding="utf-8")
    print(f"[OK] Note saved to {out}")
    return out


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("markdown_file")
    parser.add_argument("--mode", default="api")
    parser.add_argument("--source-type", default="text")
    parser.add_argument("--category", default="default")
    parser.add_argument("--out", dest="output_dir")
    args = parser.parse_args()
    make_note(args.markdown_file, mode=args.mode, source_type=args.source_type, category=args.category, output_dir=args.output_dir)
