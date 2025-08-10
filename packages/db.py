"""Database models & session factory (initial tables + vector helpers)"""
from __future__ import annotations
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, ForeignKey, Text, JSON, LargeBinary, MetaData
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os, datetime

metadata = MetaData()
Base = declarative_base(metadata=metadata)

class Document(Base):
    __tablename__ = 'documents'
    id = Column(String, primary_key=True)
    title = Column(String)
    path = Column(String, unique=True)
    mime = Column(String)
    hash = Column(String, index=True)
    tags = Column(ARRAY(String))
    version = Column(Integer, default=1)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Chunk(Base):
    __tablename__ = 'chunks'
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey('documents.id', ondelete='CASCADE'))
    ord = Column(Integer)
    text = Column(Text)
    meta_json = Column(JSON)
    embedding = Column(LargeBinary)  # TODO: alter to pgvector (vector) in migration
    document = relationship('Document', backref='chunks')

class Job(Base):
    __tablename__ = 'jobs'
    id = Column(String, primary_key=True)
    kind = Column(String)
    status = Column(String)
    payload_json = Column(JSON)
    result_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Run(Base):
    __tablename__ = 'runs'
    id = Column(String, primary_key=True)
    type = Column(String)
    status = Column(String)
    tenant_id = Column(String, nullable=True)
    inputs_json = Column(JSON)
    outputs_json = Column(JSON)
    costs_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

_DEF_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg://postgres:postgres@localhost:5432/ai_irule')
engine = create_engine(_DEF_URL, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

# CRUD / Helpers
import uuid, json, math
from typing import Sequence, Optional

def new_id() -> str:
    return str(uuid.uuid4())

def upsert_document(session, *, title: str, path: str, mime: str, hash_: str, tags, version: int, active: bool=True):
    doc = session.query(Document).filter_by(path=path).one_or_none()
    if doc and doc.hash == hash_ and not active:
        return doc, False
    if doc and doc.hash == hash_:
        return doc, False
    if doc:
        doc.hash = hash_
        doc.version = version
        doc.mime = mime
        doc.title = title
        doc.tags = tags
        doc.active = active
        session.add(doc)
        created = False
    else:
        doc = Document(id=new_id(), title=title, path=path, mime=mime, hash=hash_, tags=tags, version=version, active=active)
        session.add(doc)
        created = True
    return doc, created

def insert_chunks(session, document_id: str, chunks: Sequence[dict]):
    for i, ch in enumerate(chunks):
        session.add(Chunk(id=new_id(), document_id=document_id, ord=i, text=ch['text'], meta_json=ch.get('meta', {}), embedding=b''))

# Simple vector search placeholder (will replace with pgvector L2/ cosine)
# Accepts already embedded query vector (bytes placeholder)

def ensure_pgvector(conn):
    conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))

def vector_search(session, query_vec: bytes, top_k: int = 6):
    # Placeholder returns empty until embeddings stored as vectors
    return []

def create_job(session, kind: str, status: str = 'queued', payload: Optional[dict] = None):
    job = Job(id=new_id(), kind=kind, status=status, payload_json=payload or {}, result_json={})
    session.add(job)
    return job

def update_job_status(session, job_id: str, status: str, result: Optional[dict] = None):
    job = session.query(Job).filter_by(id=job_id).one_or_none()
    if job:
        job.status = status
        if result is not None:
            job.result_json = result
        session.add(job)
    return job

def get_job(session, job_id: str):
    return session.query(Job).filter_by(id=job_id).one_or_none()

def create_run(session, type_: str, status: str = 'queued', inputs: Optional[dict] = None):
    run = Run(id=new_id(), type=type_, status=status, inputs_json=inputs or {}, outputs_json={}, costs_json={})
    session.add(run)
    return run

def update_run(session, run_id: str, **fields):
    run = session.query(Run).filter_by(id=run_id).one_or_none()
    if run:
        for k, v in fields.items():
            if hasattr(run, k):
                setattr(run, k, v)
        session.add(run)
    return run

def get_run(session, run_id: str):
    return session.query(Run).filter_by(id=run_id).one_or_none()

def list_runs(session, limit: int = 100):
    return session.query(Run).order_by(Run.created_at.desc()).limit(limit).all()

def list_jobs(session, limit: int = 100):
    return session.query(Job).order_by(Job.created_at.desc()).limit(limit).all()

def make_all():
    Base.metadata.create_all(engine)

if __name__ == '__main__':
    make_all()
