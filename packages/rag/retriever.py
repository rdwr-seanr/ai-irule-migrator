"""Hybrid retriever.
Implements simple hybrid: keyword scan + vector (stub) then blend.
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple
from packages.db import SessionLocal, vector_search, Chunk, Document
from sqlalchemy import select
import re, math

class RetrievalResult:
    def __init__(self, chunks: List[Dict[str, Any]]):
        self.chunks = chunks
        self.citations = []

    def as_response(self):
        return {
            'chunks': self.chunks,
            'citations': self.citations
        }

# Keyword retrieval (very naive)

def keyword_candidates(session, query: str, tags) -> List[Tuple[Chunk, float]]:
    words = [w for w in re.findall(r"[A-Za-z0-9_]+", query.lower()) if len(w) > 2]
    if not words:
        return []
    stmt = select(Chunk).join(Document, Chunk.document_id == Document.id)
    if tags:
        stmt = stmt.filter(Document.tags.op("&&")(tags))
    rows = session.execute(stmt.limit(500)).scalars().all()
    scored = []
    for ch in rows:
        text_lower = ch.text.lower() if ch.text else ''
        count = sum(text_lower.count(w) for w in words)
        if count:
            scored.append((ch, float(count)))
    return scored


def blend(vector_hits: List[Dict[str, Any]], keyword_hits: List[Tuple[Chunk, float]], top_k: int):
    out = []
    # normalize keyword scores
    if keyword_hits:
        max_kw = max(s for _, s in keyword_hits) or 1.0
    else:
        max_kw = 1.0
    # index vector hits
    for vh in vector_hits:
        out.append({'chunk': vh.get('chunk'), 'score_vec': vh.get('score', 0.0), 'score_kw': 0.0})
    # merge / update
    id_map = {o['chunk'].id: o for o in out if o.get('chunk')}
    for ch, kw_score in keyword_hits:
        if ch.id in id_map:
            id_map[ch.id]['score_kw'] = kw_score / max_kw
        else:
            out.append({'chunk': ch, 'score_vec': 0.0, 'score_kw': kw_score / max_kw})
    for o in out:
        o['score'] = 0.65 * o['score_vec'] + 0.35 * o['score_kw']
    out.sort(key=lambda x: x['score'], reverse=True)
    return out[:top_k]


def build_citations(chunks):
    cites = []
    for ch in chunks:
        meta = ch.get('meta_json') or {}
        cites.append({
            'doc_id': meta.get('document_id'),
            'title': meta.get('title'),
            'page_or_slide': meta.get('page')
        })
    return cites


def retrieve(query: str, tags=None, top_k: int = 6) -> RetrievalResult:
    session = SessionLocal()
    try:
        # vector search placeholder
        vector_hits = []  # TODO integrate real embeddings & distance
        kw_hits = keyword_candidates(session, query, tags)
        blended = blend(vector_hits, kw_hits, top_k)
        results = []
        for item in blended:
            ch = item['chunk']
            results.append({
                'id': ch.id,
                'text': ch.text,
                'meta_json': ch.meta_json,
                'score': item['score']
            })
    finally:
        session.close()
    rr = RetrievalResult(chunks=results)
    rr.citations = build_citations(results)
    return rr
