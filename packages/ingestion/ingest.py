"""Ingestion pipeline.

Responsibilities:
- Walk path & collect files by allowed extensions
- Hash (SHA256) & dedupe vs DB
- Load -> chunk -> embed -> upsert (documents, chunks tables)
- Handle versioning & replace flag
"""

from pathlib import Path
import hashlib
from typing import List, Optional
from packages.db import SessionLocal, upsert_document, insert_chunks
from packages.settings import settings
import mimetypes, uuid, time

ALLOWED_EXT = {'.pdf', '.pptx', '.docx', '.txt', '.md'}

class IngestResult:
    def __init__(self, files_indexed: int, skipped: int):
        self.files_indexed = files_indexed
        self.skipped = skipped


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def collect_files(path: Path) -> List[Path]:
    return [p for p in path.rglob('*') if p.is_file() and p.suffix.lower() in ALLOWED_EXT]


def chunk_text(text: str, target_tokens: int = 600, overlap: int = 60):
    # naive split by paragraphs
    paras = text.split('\n\n')
    chunks = []
    buf = []
    length = 0
    for p in paras:
        l = len(p.split())
        if length + l > target_tokens and buf:
            joined = '\n\n'.join(buf)
            chunks.append({"text": joined})
            buf = []
            length = 0
        buf.append(p)
        length += l
    if buf:
        chunks.append({"text": '\n\n'.join(buf)})
    return chunks


def load_file(path: Path) -> str:
    # TODO: add pdf, pptx, docx specialized loaders
    try:
        return path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return path.read_bytes()[:0].decode('utf-8', errors='ignore')


def embed_texts(texts):
    # TODO: call OpenAI embedding model; return list[bytes] or list[floats]
    return [b'' for _ in texts]


def next_version(session, path: Path):
    # TODO: query existing versions
    return 1


class IngestStats(IngestResult):
    duration_sec: float | None = None


def ingest_path(path: str, tags: Optional[List[str]] = None, replace: bool = False) -> IngestResult:
    start = time.time()
    base = Path(path)
    files = collect_files(base)
    session = SessionLocal()
    indexed = 0
    skipped = 0
    try:
        for fp in files:
            raw = fp.read_bytes()
            h = sha256_bytes(raw)
            text = load_file(fp)
            version = next_version(session, fp)
            doc, created = upsert_document(session,
                                           title=fp.name,
                                           path=str(fp),
                                           mime=mimetypes.guess_type(fp.name)[0] or 'text/plain',
                                           hash_=h,
                                           tags=tags or [],
                                           version=version,
                                           active=True)
            if not created and not replace:
                skipped += 1
                continue
            chunks = chunk_text(text)
            insert_chunks(session, doc.id, chunks)
            indexed += 1
        session.commit()
    finally:
        session.close()
    return IngestResult(files_indexed=indexed, skipped=skipped)

if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument('--path', required=True)
    ap.add_argument('--tags', default='')
    ap.add_argument('--replace', action='store_true')
    args = ap.parse_args()
    tags = [t for t in args.tags.split(',') if t]
    res = ingest_path(args.path, tags=tags, replace=args.replace)
    print(json.dumps({"files_indexed": res.files_indexed, "skipped": res.skipped}))
