from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
import json, time
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import asyncio
from pathlib import Path
from packages.ingestion.ingest import ingest_path
from packages.rag.retriever import retrieve
from packages.agents.graph import build_graph, GraphState
from packages.tools.irule_parser import parse_irule
from packages.tools.appshape_generator import generate_appshape
from packages.db import SessionLocal, create_job, update_job_status, get_job, create_run, update_run, get_run, list_runs, list_jobs
from packages.observability.logging import configure_logging
from packages.observability.tracing import configure_tracing, get_tracer
from packages.settings import settings
import time

app = FastAPI(title="ai-irule-migrator")

# In-memory stubs (replace with DB / queue)
INGEST_JOBS = None  # deprecated
MIGRATE_RUNS = None

_graph = None

@app.on_event('startup')
async def _init_graph():
    global _graph
    try:
        configure_logging()
        configure_tracing()
        _graph = build_graph()
    except Exception:
        _graph = None

class IngestRequest(BaseModel):
    tags: Optional[List[str]] = None
    replace: Optional[bool] = False

class QARequest(BaseModel):
    question: str
    tags: Optional[List[str]] = None
    top_k: int = 6

@app.post('/v1/ingest')
async def ingest(files: List[UploadFile] = File(...), tags: Optional[str] = None, replace: bool = False, background: BackgroundTasks = BackgroundTasks()):
    tracer = get_tracer('api')
    with tracer.start_as_current_span('ingest_request'):
        session = SessionLocal()
        job = create_job(session, kind='ingest')
        session.commit()
        job_id = job.id
        async def process(job_id: str):
            s = SessionLocal()
            try:
                update_job_status(s, job_id, 'processing')
                s.commit()
                tmp_dir = Path('storage/tmp')
                tmp_dir.mkdir(parents=True, exist_ok=True)
                for f in files:
                    dest = tmp_dir / f.filename
                    dest.write_bytes(await f.read())
                res = ingest_path(str(tmp_dir), tags=tags.split(',') if tags else None, replace=replace)
                update_job_status(s, job_id, 'completed', result={"indexed": res.files_indexed, "skipped": res.skipped})
                s.commit()
            except Exception as e:
                update_job_status(s, job_id, 'failed', result={"error": str(e)})
                s.commit()
            finally:
                s.close()
        background.add_task(asyncio.create_task, process(job_id))
        session.close()
        return {"job_id": job_id}

@app.get('/v1/ingest/{job_id}')
async def ingest_status(job_id: str):
    s = SessionLocal()
    try:
        job = get_job(s, job_id)
        if not job:
            raise HTTPException(404, 'job not found')
        return {"id": job.id, "status": job.status, "result": job.result_json}
    finally:
        s.close()

@app.post('/v1/migrate')
async def migrate(file: UploadFile = File(...)):
    if file.size and (file.size / (1024*1024)) > settings.max_file_size_mb:
        raise HTTPException(413, 'file too large')
    tracer = get_tracer('api')
    with tracer.start_as_current_span('migrate_request'):
        session = SessionLocal()
        run = create_run(session, type_='migrate', status='processing')
        session.commit()
        run_id = run.id
        code = (await file.read()).decode('utf-8', errors='ignore')
        if _graph:
            from packages.agents.graph import GraphState  # local import to avoid circular
            state = GraphState(irule_code=code)
            result = _graph.invoke(state)  # type: ignore
            update_run(session, run_id, status='completed', outputs_json={'report': result.report, 'script': result.script})
        else:
            parsed = parse_irule(code)
            gen = generate_appshape(parsed['ast'], {"status": "partial"})
            update_run(session, run_id, status='completed', outputs_json={'report': {"diagnostics": parsed['diagnostics']}, 'script': gen['code']})
        session.commit()
        session.close()
        return {"run_id": run_id}

@app.get('/v1/migrate/{run_id}')
async def migrate_status(run_id: str):
    s = SessionLocal()
    try:
        run = get_run(s, run_id)
        if not run:
            raise HTTPException(404, 'run not found')
        return {"id": run.id, "status": run.status, "outputs": run.outputs_json}
    finally:
        s.close()

@app.post('/v1/qa')
async def qa(req: QARequest):
    if _graph:
        state = GraphState(question=req.question)
        result = _graph.invoke(state)  # type: ignore
        return {"answer": result.answer, "citations": result.citations or []}
    rr = retrieve(req.question, tags=req.tags, top_k=req.top_k)
    return {"answer": "Placeholder answer", "citations": rr.citations}

@app.get('/v1/runs')
async def runs():
    s = SessionLocal()
    try:
        runs_ = list_runs(s, limit=100)
        jobs_ = list_jobs(s, limit=100)
        items = [{"id": r.id, "type": r.type, "status": r.status, "created_at": r.created_at.isoformat()} for r in runs_]
        items += [{"id": j.id, "type": j.kind, "status": j.status, "created_at": j.created_at.isoformat()} for j in jobs_]
        return {"items": items}
    finally:
        s.close()

@app.get('/v1/migrate/{run_id}/stream')
async def migrate_stream(run_id: str):
    async def event_stream():
        while True:
            s = SessionLocal()
            try:
                run = get_run(s, run_id)
                if not run:
                    yield f"event: error\ndata: {json.dumps({'error':'not found'})}\n\n"
                    return
                payload = {"id": run.id, "status": run.status}
                yield f"data: {json.dumps(payload)}\n\n"
                if run.status in ('completed','failed'):
                    return
            finally:
                s.close()
            await asyncio.sleep(1)
    return StreamingResponse(event_stream(), media_type='text/event-stream')

# Rate limiter store (simple in-memory token bucket per IP)
_rate_state = {}

def rate_limiter(ip: str):
    now = time.time()
    conf_window = 60
    refill_rate = settings.rate_limit_per_min / conf_window
    bucket = _rate_state.get(ip, {"tokens": settings.rate_limit_per_min, "ts": now})
    elapsed = now - bucket['ts']
    bucket['tokens'] = min(settings.rate_limit_per_min, bucket['tokens'] + elapsed * refill_rate)
    bucket['ts'] = now
    if bucket['tokens'] < 1:
        _rate_state[ip] = bucket
        raise HTTPException(429, 'rate limit exceeded')
    bucket['tokens'] -= 1
    _rate_state[ip] = bucket

@app.middleware('http')
async def _rl_mw(request, call_next):
    client_ip = request.client.host if request.client else 'unknown'
    try:
        rate_limiter(client_ip)
    except HTTPException as e:
        return HTTPException(status_code=e.status_code, detail=e.detail)
    return await call_next(request)
