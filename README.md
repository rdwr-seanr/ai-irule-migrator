# ai-irule-migrator

LangGraph / LangChain based service to ingest curated developer docs and migrate F5 iRules → Radware AppShape++ with reports and QA via RAG.

Highlights
- Ingestion: PDFs, PPTX, DOCX, TXT, MD; de-dup + versioning.
- Retrieval: Hybrid (keyword + vector stub today) with citations.
- Migration: parse → capability map → plan → translate → verify → report.
- Guardrails: Emits only known mappings from curated data; unknowns are reported, not hallucinated.
- API + Web UI: Upload iRules, run QA, and ingest docs from the browser.

Important notes
- Vector search and embeddings are scaffolded; QA quality improves after enabling pgvector + OpenAI embeddings per docs/ROADMAP.md.
- Capability mappings live in `packages/tools/capability_map.json` and can be extended by admins.

Getting Started
- Requirements: Docker (for Postgres/pgvector), Python 3.11, Node not required.

1) Configure environment
```
cp .env.template .env
# Edit .env: set OPENAI_API_KEY and optional DATABASE_URL
```

2) Start Postgres (pgvector image)
```
docker compose up -d postgres-pgvector
```

3) Create virtualenv and install
```
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

4) Initialize DB tables (temporary until Alembic migrations are added)
```
python packages/db.py
```

5) Run the API
```
uvicorn apps.api.main:app --reload --port 8080
```

Using the Web UI
- Open http://localhost:8080/
- Migrate iRule: Select a `.tcl` or `.txt` file and click “Convert to AppShape++”.
- Ask Your Docs (QA): Type a question; citations are shown below the answer.
- Ingest Documentation: Upload PDFs/PPTX/DOCX/TXT/MD with optional comma-separated tags. Use this to improve QA and future mapping coverage.

Using the API directly
- Ingest
```
curl -X POST http://localhost:8080/v1/ingest \
  -F files=@docs/AlteonOS-34-5-4-AppShape-Ref.pdf \
  -F tags=base,reference
# Poll job:
curl http://localhost:8080/v1/ingest/<job_id>
```

- QA (RAG)
```
curl -X POST http://localhost:8080/v1/qa \
  -H 'Content-Type: application/json' \
  -d '{"question":"How are HTTP headers mapped?"}'
```

- Migrate an iRule
```
curl -X POST http://localhost:8080/v1/migrate -F file=@/path/to/your.irule
# Then fetch the run status/output:
curl http://localhost:8080/v1/migrate/<run_id>
```

CLI alternatives
- Ingest a folder of docs (ingests allowed file types under ./docs):
```
python -m packages.ingestion.ingest --path ./docs --tags base,reference
```
- Watch a folder and auto-ingest on changes:
```
python -m packages.ingestion.watcher --path ./docs --interval 2
```

Admin: Extending capability mappings
- File: `packages/tools/capability_map.json` (loaded by the generator at runtime).
- Add entries like:
```
{
  "HTTP::header": {"target": "set_header", "source": "docs/AlteonOS-34-5-4-AppShape-Ref.pdf"},
  "HTTP::method": {"target": "get_method", "source": "<doc_or_page_ref>"}
}
```
- Only mapped constructs are emitted; others remain commented with “unmapped”.

Repository Layout
```
apps/api              # FastAPI app (+ static web UI)
packages/ingestion    # ingestion + loaders
packages/rag          # retrieval logic
packages/agents       # LangGraph wiring
packages/tools        # parsing & generation tools
packages/schemas      # Pydantic models
packages/tests        # test suite
docs/                 # your ingested/reference docs
storage/              # local object store / temp uploads
```

Troubleshooting
- Postgres connection error: Ensure `docker compose up -d postgres-pgvector` and `DATABASE_URL` matches the exposed port (default 5432).
- 413 on migrate upload: File exceeds `MAX_FILE_SIZE_MB` in settings; adjust `.env` if needed.
- QA returns placeholders: Embeddings are not enabled yet; follow docs/ROADMAP.md to enable pgvector + embeddings.

Roadmap
- See docs/ROADMAP.md for best practices, gaps, and next steps.
