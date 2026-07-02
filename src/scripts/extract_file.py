from __future__ import annotations

from pathlib import Path
import re

import fitz
import trafilatura
from bs4 import BeautifulSoup

from scripts.config import ensure_dirs
from scripts.path_router import processed_markdown_path, resolve_input_file


def clean_text(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def read_md_txt(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='ignore')


def read_pdf_pymupdf(path: Path) -> str:
    doc = fitz.open(str(path))
    parts = []
    for i, page in enumerate(doc):
        text = page.get_text('text')
        if text.strip():
            parts.append(f'\n\n#### Page {i + 1}\n\n{text}')
    return clean_text('\n'.join(parts))


def read_pdf_docling(path: Path) -> str:
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(path))
        return result.document.export_to_markdown()
    except Exception as exc:
        print(f'[WARN] Docling failed, fallback to PyMuPDF: {exc}')
        return read_pdf_pymupdf(path)


def read_html(path: Path) -> str:
    html = path.read_text(encoding='utf-8', errors='ignore')
    extracted = trafilatura.extract(html, output_format='markdown', include_comments=False, include_tables=True)
    if extracted:
        return clean_text(extracted)

    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()
    return clean_text(soup.get_text('\n'))


def read_subtitle(path: Path) -> str:
    text = path.read_text(encoding='utf-8', errors='ignore')
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.upper() == 'WEBVTT' or '-->' in s or s.isdigit() or re.match(r'^\d{2}:\d{2}:\d{2}', s):
            continue
        lines.append(s)
    return clean_text('\n'.join(lines))


def extract_to_markdown(
    file_path: str,
    source_type: str = 'text',
    category: str = 'default',
    trusted_path: bool = False,
) -> Path:
    ensure_dirs()
    path = Path(file_path).expanduser().resolve() if trusted_path else resolve_input_file(file_path, source_type=source_type)
    suffix = path.suffix.lower()

    if suffix in ['.md', '.txt']:
        content = read_md_txt(path)
    elif suffix == '.pdf':
        content = read_pdf_docling(path)
    elif suffix in ['.html', '.htm']:
        content = read_html(path)
    elif suffix in ['.srt', '.vtt']:
        content = read_subtitle(path)
    else:
        raise ValueError(f'Unsupported file type: {suffix}')

    out = processed_markdown_path(path.name, source_type=source_type, category=category)
    final = f'''#### {path.stem}

##### 来源
- source_type: {source_type}
- category: {category}
- source: {path}

---

{content}
'''
    out.write_text(final, encoding='utf-8')
    print(f'[OK] Extracted to {out}')
    return out


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('--source-type', default='text')
    parser.add_argument('--category', default='default')
    args = parser.parse_args()
    extract_to_markdown(args.file, source_type=args.source_type, category=args.category)
