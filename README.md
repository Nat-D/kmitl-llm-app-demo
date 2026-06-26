# KMITL · LLM App Demo

A **mini, readable chat + RAG app** — the reference implementation for *Building
LLM-Powered Applications*. It's deliberately small (one sitting to read end-to-end),
uses **no LLM framework**, and its corpus is the course's own stack, so it can answer
questions about how it itself works.

> It is a **reference to learn from, not a homework answer to submit.** Your project
> must run on a *different* corpus, with *your own* evaluation set you can defend.
> See [Using this in the course](#using-this-in-the-course).

## Quickstart

```bash
uv sync                                             # install deps
cp .env.example .env                                # then put your course LiteLLM key in .env
uv run python -m app.ingest corpus                  # chunk + embed corpus/ (needs the key)
uv run uvicorn app.main:app --reload --port 8000    # http://localhost:8000
```

Both chat and embeddings go through the class LiteLLM proxy — one base URL, one key
(get it from your course Profile page). `OpenAI()` reads them from the environment.

## What each file is (and the lecture it maps to)

Read in this order — it's also the course order:

| File | Lecture | What you'll recognise |
|---|---|---|
| `app/llm.py` | L1–L4 | the only place we call a model: `chat_stream()` + `embed()` |
| `app/main.py`, `web/app.js` | L3–L4 | `POST /api/chat` Server-Sent Events, end to end |
| `app/llm.py` `extract_from_image` + `/api/extract` | L2 | **multimodal**: read a document image → structured JSON (parse + repair) |
| `app/store.py`, `app/ingest.py` | L5 | embeddings → a vector store in ~100 lines; `min_score` floor |
| `app/rag.py` | L6 | retrieve → numbered context → stream a **cited** answer |
| `eval/` | L7–L8 | Recall@k / MRR / nDCG + LLM-as-judge over a labelled set |
| `agent/loop.py` | L10+ | the call → run-tool → feed-back loop |
| `tests/` | (testing lecture) | unit tests + in-process e2e tests, run in CI |

See **[CODE_TOUR.md](CODE_TOUR.md)** for the guided read.

## Built stage by stage

The repo grows the way the course does — one git tag per stage:

| tag | adds |
|---|---|
| `l03-chat` | a streaming chat endpoint + web UI |
| `l05-index` | embeddings + the vector store + ingest |
| `l06-rag` | retrieval, the `min_score` floor, and citations |
| `l07-eval` | the evaluation harness |
| `l10-agent` | the tool-calling agent loop |

`git checkout l06-rag` to see exactly that stage; `git diff l05-index l06-rag` *is*
the "what RAG adds" lesson.

## Optional: Postgres + pgvector (with Alembic migrations)

The default store is SQLite (zero setup, easy to read). The **production swap** is
Postgres + `pgvector` — same `Hit` / `connect` / `add` / `search` interface, but the
nearest-neighbour search runs in the database. Schema changes are managed with
**Alembic migrations** instead of `CREATE TABLE` by hand:

```bash
docker compose up -d                 # Postgres + pgvector on host port 55432
uv sync --group pg                   # driver + pgvector + alembic
export DATABASE_URL=postgresql://rag:rag@localhost:55432/ragdemo
alembic upgrade head                                # create the schema via a migration
uv run python -m app.ingest corpus                  # embed the corpus into Postgres
uv run uvicorn app.main:app --reload --port 8000    # the app now uses pgvector
```

The host port is **55432** (not the standard 5432) so it won't clash with a Postgres
already running on your machine. `app/store_pg.py` is the pgvector store, `alembic/`
holds the migration that owns the schema, and `app/vectorstore.py` is the one-line
switch: set `DATABASE_URL` and the whole app uses Postgres — nothing else changes.

## The router → service → repository pattern (`examples/`)

The app itself is intentionally **flat** (`main.py` + a few modules) so it reads in one
sitting. But a growing backend wants the three-layer "house style": **router** (HTTP
only) → **service** (business logic) → **repository** (pure data access). `examples/`
shows it on its own, runnable over in-memory SQLite:

- `examples/orm_repository.py` — a SQLAlchemy **ORM** model + a repository (the data
  layer the app skips; the table an Alembic migration would own).
- `examples/layering.py` — router → service → repository wired together, with the
  service unit-tested by a plain call (a fake client, no HTTP) — the payoff of the split.

```bash
uv run --group pg python -m examples.orm_repository   # ORM model + repository round-trip
uv run --group pg python -m examples.layering         # router → service → repository, tested without HTTP
```

See **[examples/README.md](examples/README.md)** for a step-by-step guide (prerequisites,
expected output, what to read for) — including running the Alembic migration against
Postgres + pgvector.

## Using this in the course

This app shows the **patterns**; your graded work applies them to a **different
problem**. Concretely, to pass the project you must:

1. use a corpus this app can't answer (your own domain, raw data committed);
2. build your own evaluation set (~30 examples) and beat a baseline you name;
3. show one measured improvement over a naive default (e.g. justify your `min_score`);
4. defend it live — run it on a new input and explain one design choice + one number.

Reading, running, forking, and citing this repo is encouraged. Submitting it (or a
re-skin) as your own is not.
