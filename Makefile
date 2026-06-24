.PHONY: run ingest eval test
# Thin aliases — read these to see the real commands.

run:        ## serve the app at http://localhost:8000
	uv run uvicorn app.main:app --reload --port 8000

ingest:     ## chunk + embed corpus/ into the vector store
	uv run python -m app.ingest corpus

eval:       ## score retrieval (Recall@k / MRR / nDCG) + LLM-judge
	uv run python -m eval.eval

test:       ## run unit + e2e tests (no network — the LLM is stubbed)
	uv run pytest -q
