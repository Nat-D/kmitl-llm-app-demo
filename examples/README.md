# Runnable backend-pattern demos

The app itself is intentionally **flat** (`../app/`) so it reads in one sitting. These
standalone scripts show the patterns a bigger backend grows into — the
**router → service → repository** layering, an **ORM**, and **Alembic migrations** —
each runnable on its own with one command.

They are *local* demos (you run them from a clone), not endpoints on the hosted demo.

## Prerequisites

```bash
# from the repo root
uv sync --group pg      # installs SQLAlchemy + Alembic + the Postgres driver
```

> The default app is SQLite-only and needs none of this. These demos use SQLAlchemy
> (the ORM) and Alembic (migrations), which live in the optional `pg` dependency group.
> The in-browser sandbox doesn't have SQLAlchemy, which is why these run locally.

---

## 1. ORM + repository — `orm_repository.py`

The **data layer** the app skips: a SQLAlchemy ORM model + a repository (pure data
access, no business logic). It runs over an in-memory SQLite database, so there's
nothing to set up.

```bash
uv run --group pg python -m examples.orm_repository
```

Expected output (the two turns written through the repository, read back newest-first):

```
[2] u1: 'and embeddings?' -> 'Vectors that place similar text '
[1] u1: 'what is RAG?' -> 'Retrieval-augmented generation g'
```

What to read for:
- `class Conversation(Base)` — the **ORM model** (`Mapped[...]` typed columns). This maps
  to a table that, in production, an Alembic migration creates (see demo 3).
- `class ConversationRepository` — **pure data access**: `add()` and `recent()`, nothing
  else. The service calls these; the router never touches the database.

## 2. Layering: router → service → repository — `layering.py`

The three layers wired together, and the payoff: you **unit-test the service** with a
plain call — a fake model client and an in-memory repository, no HTTP, no FastAPI.

```bash
uv run --group pg python -m examples.layering
```

Expected output:

```
(stub answer to: what is a vector store?)
saved turns: ['what is a vector store?']
```

What to read for:
- `class ChatService` — the **business logic** ("fat middle"): it takes the model client
  and the repository by injection, calls the model, and saves the turn.
- The commented `router` block — **HTTP only** (parse request → call the service → map
  errors to status codes). It's commented out because running it needs a server; the
  point is the *shape*.
- `__main__` builds the service with a `FakeLLM` and calls `service.reply(...)` directly.
  That's the whole argument for the split: the interesting layer is testable in isolation.

## 3. Migrations with Alembic (Postgres + pgvector)

A real backend lets **migrations** own the schema — ordered, reviewable, reversible —
instead of `CREATE TABLE` by hand. This demo needs Docker (for Postgres + pgvector).

```bash
# from the repo root
docker compose up -d                                   # Postgres + pgvector on port 55432
export DATABASE_URL=postgresql://rag:rag@localhost:55432/ragdemo
make migrate                                           # = alembic upgrade head
```

`make migrate` runs the single revision in `../alembic/versions/0001_create_chunks.py`,
which creates the `chunks` table with a `vector(1024)` column. Check it worked:

```bash
uv run --group pg alembic current     # -> 0001 (head)
uv run --group pg alembic history     # -> <base> -> 0001 (head), create the chunks table ...
```

Now the whole app runs on pgvector instead of SQLite (same code, `DATABASE_URL` is the
only switch):

```bash
make ingest && make run        # ingest embeds the corpus into Postgres; open http://localhost:8000
```

To roll the migration back: `uv run --group pg alembic downgrade -1` (drops the table).
Tear down Postgres when done: `docker compose down -v`.

What to read for:
- `../alembic/versions/0001_create_chunks.py` — the `upgrade()` / `downgrade()` pair.
- `../app/store_pg.py` — the pgvector store (same `Hit`/`connect`/`add`/`search` interface
  as the SQLite one); `../app/vectorstore.py` is the one-line `DATABASE_URL` switch.

---

### One-step aliases (from the repo root)

```bash
make demo-orm        # = uv run --group pg python -m examples.orm_repository
make demo-layering   # = uv run --group pg python -m examples.layering
make migrate         # = alembic upgrade head   (needs docker compose up + DATABASE_URL)
```
