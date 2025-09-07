# Best Practices & Roadmap

Principles
- Non‑hallucination: Emit AppShape++ only for constructs present in the curated capability map. Unknowns remain commented and are reported.
- Data provenance: Every mapping carries a source citation (document/page/slide); QA returns citations.
- Deterministic runs: Same input + same dataset → same output.
- Safety first: Rate limits, size limits, MIME allowlist, and admin‑only operations for ingestion/mapping.
- Observability: Structured JSON logs and OpenTelemetry tracing hooks.

Immediate Gaps
1) Vector DB + embeddings
- Current state: `Chunk.embedding` is a binary placeholder; `vector_search()` is a stub.
- Goal: Store embeddings in pgvector and perform ANN search with cosine/L2 distance; blend with keyword retrieval.
- Tasks:
  - Add Alembic migrations to create `vector(EMBED_DIM)` column and IVFFLAT index; ensure `CREATE EXTENSION IF NOT EXISTS vector`.
  - Implement `embed_texts()` using OpenAI `text-embedding-3-large` with batching and retries.
  - Implement `vector_search()` using SQL distance; update `retriever.blend()` as needed.
- Acceptance:
  - QA returns semantically relevant chunks with citations across doc types.
  - Ingestion stores vectors and retrieval latency remains reasonable (<300 ms per query with warm cache).

2) Parser coverage
- Current state: Minimal event/command detection; simple diagnostics.
- Goal: Parse conditionals (if/elseif/else), switch, expression operands, and common `HTTP::*` variants with line numbers and raw text.
- Tasks:
  - Extend AST structure to represent blocks, conditions, and arguments.
  - Add unit tests covering varied iRule samples (headers, URI rewrite, classes, regexps).
- Acceptance:
  - Coverage metrics in reports reflect actual mappable nodes vs total nodes.
  - Parser robust to whitespace/comments and multi‑line constructs.

3) Generation + verification
- Current state: Generator uses curated mapping; verification only counts unmapped.
- Goal: Grammar‑aligned templates for AppShape++ and a verifier that flags syntax mismatches before returning output.
- Tasks:
  - Define templates per mapping (argument shapes, constraints) in the capability dataset.
  - Add a static verifier to check each emitted line against its template.
  - Include verification results and confidence in the migration report.
- Acceptance:
  - No invalid constructs are emitted; report declares success/partial/blocked with unmapped details.

4) Tests & quality
- Current state: Minimal test.
- Goal: Golden tests for representative iRules, property tests for invariants, and fast unit coverage.
- Tasks:
  - Golden files for parse → plan → translate → verify.
  - Property tests: unknown nodes are never emitted; mapping entries always produce allowed targets.
- Acceptance:
  - CI runs tests reliably; contributors can iterate quickly.

5) UI & auth
- Current state: Minimal web UI; no auth.
- Goal: Client‑friendly workflows and admin protections.
- Tasks:
  - Add auth (token/header) to ingest and mapping update endpoints.
  - Improve report rendering (coverage %, unmapped table with line links).
  - Add admin UI to edit `packages/tools/capability_map.json` safely (with validation and git‑style change preview).
- Acceptance:
  - End‑users can migrate and ask QA easily; admins can safely curate mappings and docs.

6) Deployment & ops
- Current state: Docker for Postgres; app runs locally.
- Goal: Containerized app with environment‑driven config, health checks, and metrics.
- Tasks:
  - Add Dockerfile and a compose profile for the API; add `/healthz` endpoint.
  - Export traces to OTLP endpoint; optional log shipping.
- Acceptance:
  - One‑command dev environment and predictable prod deploys.

Admin Workflows
- Update mappings: Edit `packages/tools/capability_map.json` (include `target` and `source`), commit, and redeploy.
- Ingest docs: Use the UI or `python -m packages.ingestion.ingest --path ./docs --tags <tags>`; re‑ingest after adding or updating documents.
- Rebuild indices: After enabling embeddings/pgvector, re‑ingest or backfill embeddings for existing chunks.

Definition of Done (for migration of an iRule)
- Input parsed without errors; AST has events, nodes, and line numbers.
- Plan marks status full/partial/blocked with counts.
- Generator emits only mapped constructs from the dataset with citations.
- Verifier passes (or precisely lists failures) and report includes coverage, unmapped nodes, and audit info.

Open Questions
- Scope of supported iRule features (tables, sideband, binaries) — likely remain unsupported with clear guidance.
- Multi‑tenant separation and ACL on documents/mappings.

