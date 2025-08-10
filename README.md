# ai-irule-migrator

LangGraph / LangChain based service to ingest curated developer docs and migrate F5 iRules -> AppShape++ with detailed reports & QA RAG.

## Features (MVP Scope)
- Doc ingestion: CLI, folder watch, API
- MIME loaders: pdf, pptx, docx, txt, md
- Hash + version dedupe, pgvector storage
- Hybrid retrieval with citations
- Migration graph: parse -> capability map -> plan -> translate -> verify -> report
- Partial / blocked handling with rationale
- FastAPI API + minimal UI placeholder

## Quickstart
```
cp .env.template .env  # add OpenAI key
make db.up
make setup
make ingest  # ingest ./docs
make api.run
```

### Ingest CLI
```
python -m packages.ingestion.ingest --path ./docs --tags base,reference
```

### RAG QA
```
curl -X POST http://localhost:8080/v1/qa \
  -H 'Content-Type: application/json' \
  -d '{"question":"How are HTTP headers mapped?"}'
```

### Migrate iRule
```
curl -X POST http://localhost:8080/v1/migrate \
  -F file=@sample.irule
```

## Repo Layout
```
apps/api              # FastAPI app
apps/ui               # (future) UI
packages/ingestion    # ingestion + loaders
packages/rag          # retrieval logic
packages/agents       # LangGraph wiring
packages/tools        # parsing & generation tools
packages/schemas      # Pydantic models
packages/tests        # test suite
storage/              # local object store
```

## Roadmap (abridged)
See project spec for extended roadmap.
