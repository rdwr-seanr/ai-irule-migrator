SHELL := /usr/bin/env bash

.PHONY: setup db.up ingest api.run tests format lint watch

setup:
	python -m venv .venv && . .venv/Scripts/activate && pip install -e .[dev]

db.up:
	docker compose up -d postgres-pgvector || docker-compose up -d postgres-pgvector

ingest:
	. .venv/Scripts/activate && python -m packages.ingestion.ingest --path ./docs

api.run:
	. .venv/Scripts/activate && uvicorn apps.api.main:app --reload --port 8080

tests:
	. .venv/Scripts/activate && pytest -q

watch:
	. .venv/Scripts/activate && python -m packages.ingestion.watcher --path ./docs --interval 2
