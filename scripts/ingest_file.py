from __future__ import annotations

from pathlib import Path
import hashlib
import json
from datetime import datetime

import chromadb

from scripts.config import CHROMA_COLLECTION, CHROMA_HOST, CHROMA_PORT, KB_DIR, ensure_dirs
from scripts.llm_router import local_embed

client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
collection = client.get_or_create_collection(name=CHROMA_COLLECTION)
MANIFEST = KB_DIR / 'manifest.json'


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding='utf-8'))
    return {}


def save_manifest(data: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chunk_markdown(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks: list[str] = []
    current = ''
    step = max(1, chunk_size - overlap)
    for p in paragraphs:
        if len(current) + len(p) + 2 <= chunk_size:
            current = current + '\n\n' + p if current else p
            continue
        if current:
            chunks.append(current)
        if len(p) > chunk_size:
            for start in range(0, len(p), step):
                chunks.append(p[start : start + chunk_size])
            current = ''
        else:
            current = p
    if current:
        chunks.append(current)
    return chunks


def stable_id(path: Path, idx: int, chunk: str, source_type: str, category: str) -> str:
    h = hashlib.sha256(f'{path}:{source_type}:{category}:{idx}:{chunk}'.encode('utf-8')).hexdigest()[:16]
    return f'{path.stem}-{idx}-{h}'


def ingest_markdown(file_path: str, force: bool = False, source_type: str = 'text', category: str = 'default', source: str | None = None) -> dict:
    ensure_dirs()
    path = Path(file_path).expanduser().resolve()
    h = file_hash(path)
    manifest = load_manifest()
    key = f'{path}|{source_type}|{category}'
    if not force and manifest.get(key, {}).get('hash') == h:
        print(f'[SKIP] unchanged: {path}')
        return {'skipped': True, 'chunks': manifest[key].get('chunks', 0)}
    text = path.read_text(encoding='utf-8', errors='ignore')
    chunks = chunk_markdown(text)
    if not chunks:
        print(f'[WARN] no chunks extracted from {path}')
        return {'skipped': False, 'chunks': 0}
    ids, docs, metas, embs = [], [], [], []
    now = datetime.now().isoformat(timespec='seconds')
    src = source or str(path)
    for idx, chunk in enumerate(chunks):
        ids.append(stable_id(path, idx, chunk, source_type, category))
        docs.append(chunk)
        metas.append({'source_type': source_type, 'category': category, 'source': src, 'file_name': path.name, 'file_type': path.suffix.lower(), 'chunk_index': idx, 'ingested_at': now})
        embs.append(local_embed(chunk))
    collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
    manifest[key] = {'hash': h, 'chunks': len(chunks), 'source_type': source_type, 'category': category, 'source': src, 'updated_at': now}
    save_manifest(manifest)
    print(f'[OK] Ingested {len(chunks)} chunks from {path}')
    return {'skipped': False, 'chunks': len(chunks)}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('markdown_file')
    parser.add_argument('--source-type', default='text')
    parser.add_argument('--category', default='default')
    parser.add_argument('--source')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    ingest_markdown(args.markdown_file, force=args.force, source_type=args.source_type, category=args.category, source=args.source)
