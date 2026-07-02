from __future__ import annotations

from datetime import datetime
import json
import shlex


def command_args(message: str, command: str) -> list[str]:
    """Parse args whether AstrBot keeps or strips the leading slash."""
    tokens = shlex.split(message.strip())
    if tokens and tokens[0].lstrip("/").casefold() == command.casefold():
        tokens = tokens[1:]
    return tokens


def initial_last_sent(scheduled_time: str, now: datetime) -> str:
    """Avoid an immediate catch-up push when subscribing after today's time."""
    if now.strftime("%H:%M") >= scheduled_time:
        return now.date().isoformat()
    return ""


def text_result(data: dict) -> str:
    if "answer" in data:
        return data["answer"]
    result = data.get("result", data)
    if isinstance(result, dict):
        for key in ("plan", "patch", "note", "markdown", "dir"):
            if key in result:
                return str(result[key])
    return json.dumps(data, ensure_ascii=False, indent=2)


def file_result(data: dict) -> str:
    result = data.get("result", data)
    if not isinstance(result, dict):
        return text_result(data)
    lines = ["Processed."]
    if result.get("markdown"):
        lines.append(f"Markdown: {result['markdown']}")
    if result.get("note"):
        lines.append(f"Note: {result['note']}")
    ingest = result.get("ingest")
    if isinstance(ingest, dict):
        lines.append(f"Chunks: {ingest.get('chunks', 0)}")
    return "\n".join(lines)


def parse_out(args: list[str]) -> tuple[list[str], str | None]:
    if "--out" not in args:
        return args, None
    idx = args.index("--out")
    if idx == len(args) - 1:
        raise ValueError("--out requires a value")
    output_dir = args[idx + 1]
    return args[:idx] + args[idx + 2 :], output_dir


def split_message(text: str, max_chars: int = 500) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= max_chars:
            current = paragraph
            continue
        lines = paragraph.splitlines()
        current = ""
        for line in lines:
            candidate = line if not current else f"{current}\n{line}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = line[:max_chars]
    if current:
        chunks.append(current)
    return chunks
