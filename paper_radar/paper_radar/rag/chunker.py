from __future__ import annotations


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    paragraphs = [value.strip() for value in text.split("\n\n") if value.strip()]
    chunks: list[str] = []
    current = ""
    step = max(1, chunk_size - overlap)
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= chunk_size:
            current = f"{current}\n\n{paragraph}" if current else paragraph
            continue
        if current:
            chunks.append(current)
        if len(paragraph) > chunk_size:
            chunks.extend(
                paragraph[start : start + chunk_size]
                for start in range(0, len(paragraph), step)
            )
            current = ""
        else:
            current = paragraph
    if current:
        chunks.append(current)
    return chunks
