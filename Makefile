.PHONY: run ingest eval judge test pg-up migrate
# Thin aliases — read these to see the real commands.

run:        ## serve the app at http://localhost:8000
	uv run uvicorn app.main:app --reload --port 8000

ingest:     ## chunk + embed corpus/ into the vector store
	uv run python -m app.ingest corpus

eval:       ## score retrieval: Recall@k / MRR / nDCG
	uv run python -m eval.eval

judge:      ## LLM-as-judge on answer quality (faithfulness / relevance)
	uv run python -m eval.judge

test:       ## run unit + e2e tests (no network — the LLM is stubbed)
	uv run pytest -q

# --- optional Postgres + pgvector path (see docker-compose.yml) -------------------
pg-up:      ## start Postgres + pgvector (host port 55432)
	docker compose up -d

migrate:    ## create/upgrade the Postgres schema via Alembic (needs DATABASE_URL)
	uv run --group pg alembic upgrade head
