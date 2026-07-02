from __future__ import annotations

import chromadb

from scripts.config import CHROMA_COLLECTION, CHROMA_HOST, CHROMA_PORT
from scripts.llm_router import generate, local_embed

client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
collection = client.get_or_create_collection(name=CHROMA_COLLECTION)


def build_where(source_type: str | None = None, category: str | None = None) -> dict | None:
    clauses = []
    if source_type:
        clauses.append({'source_type': source_type})
    if category:
        clauses.append({'category': category})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {chr(36) + chr(97) + chr(110) + chr(100): clauses}


def query_kb(question: str, n_results: int = 6, mode: str = 'api', show_sources: bool = True, source_type: str | None = None, category: str | None = None) -> str:
    q_emb = local_embed(question)
    kwargs = {'query_embeddings': [q_emb], 'n_results': n_results, 'include': ['documents', 'metadatas', 'distances']}
    where = build_where(source_type=source_type, category=category)
    if where:
        kwargs['where'] = where
    result = collection.query(**kwargs)
    docs = result.get('documents', [[]])[0]
    metas = result.get('metadatas', [[]])[0]
    distances = result.get('distances', [[]])[0]
    if not docs:
        return 'No related content was found in the local knowledge base.'

    context_parts, source_lines = [], []
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances), start=1):
        source = meta.get('source', '')
        chunk_idx = meta.get('chunk_index', '')
        st = meta.get('source_type', '')
        cat = meta.get('category', '')
        context_parts.append(f'[{i}] source_type={st} category={cat} source={source} chunk={chunk_idx} distance={dist}\n{doc}')
        source_lines.append(f'- [{i}] {st}/{cat} | {source} | chunk={chunk_idx} | distance={dist:.4f}')

    context = '\n\n---\n\n'.join(context_parts)
    prompt = f'''You are a rigorous local RAG assistant.
Answer in Chinese. Use only Markdown headings #### and #####.
Use only the retrieved context below. If the context is insufficient, say clearly that the knowledge base does not contain enough information. Do not invent facts.

Question:
{question}

Retrieved context:
{context}
'''
    answer = generate(prompt, mode=mode)
    if show_sources:
        answer += '\n\n#### Sources\n' + '\n'.join(source_lines)
    print(answer)
    return answer


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('question')
    parser.add_argument('--mode', default='api')
    parser.add_argument('--source-type')
    parser.add_argument('--category')
    parser.add_argument('--n-results', type=int, default=6)
    args = parser.parse_args()
    query_kb(args.question, mode=args.mode, source_type=args.source_type, category=args.category, n_results=args.n_results)
