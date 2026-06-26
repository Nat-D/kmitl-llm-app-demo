# Code tour

Read the files in this order — it's the dependency order, and roughly the course
order. The whole thing is ~900 lines; you can read it in one sitting.

### 1. `app/llm.py` — the only place we call a model
Two functions: `chat_stream()` (yields tokens) and `embed()` (text → vector). The
"LLM integration" is just the OpenAI client pointed at the class proxy. Notice the
client is built lazily so tests can import the app without a key.

### 2. `app/store.py` — a vector database in ~90 lines
SQLite holds each chunk + its embedding; `search()` ranks by cosine similarity in
NumPy and applies the **`min_score` floor**. Read the comment on the floor — it's the
single most important RAG safety knob. (Production swap: pgvector / sqlite-vec, same
`add`/`search` shape.)

### 3. `app/ingest.py` + `corpus/` — watch documents become vectors
`chunk_text()` is deliberately naive (fixed-size windows). Run `uv run python -m app.ingest corpus` and the
10 markdown docs about this app's own stack become rows in `data/store.db`.
*Naive chunking is the obvious thing to improve — measure it with `eval/`.*

### 4. `app/rag.py` — the heart of it
`answer()` is the whole of "RAG": embed the question → retrieve chunks above the floor
→ format them as a **numbered list** in the prompt → stream a **cited** answer. If
nothing clears the floor it refuses ("I don't know") instead of hallucinating.

### 5. `app/main.py` + `web/app.js` — wire it to a browser with SSE
`POST /api/chat` streams `data: {"token": ...}` frames, then `[DONE]`. `web/app.js` is
the buffer-and-split reader from the SSE lecture — network chunks don't line up with
frames, so we stitch them. The `use_rag` toggle lets you show the same question with
and without retrieval.

### 5b. `app/llm.py extract_from_image` + `/api/extract` — multimodal (Lecture 2)
`gemma-4-E4B-it` is multimodal, so the 📎 panel uploads a document image and the model
reads it. We pass the image as a `data:` URL in the message and ask for JSON, then
*parse it with one repair retry* — the same structured-output discipline as text, just
with an image in the prompt. (`response_format` is ignored by the proxy, so we coax and
parse rather than enforce a schema.)

### 6. `eval/` — now prove it works
`eval.py` scores the retriever (Recall@k / MRR / nDCG) against `qrels.jsonl`; `judge.py`
is an LLM-as-judge for answer quality. On this small, clean corpus the retrieval scores
are near-perfect — the real headroom shows up on a **messier corpus** (your project),
which is exactly when this harness earns its keep. Change the chunking, re-run, compare.

### 7. `agent/loop.py` — a tool-using loop
The call → run-tool → feed-the-result-back loop, with a stop condition, written plainly
(a tiny text protocol instead of the provider's function-calling API, so it works with
any model). The one tool searches the notes.

### 8. `tests/` — how we know it works
- `test_unit.py`: pure logic (chunking, cosine + floor, metrics) — no network.
- `test_e2e.py`: drives the real FastAPI app in-process with `httpx`, with the LLM
  **stubbed**, and asserts the SSE the browser would receive. This is why CI needs no
  key. `uv run pytest -q`.

## Extension seams (each is a later lecture / a project idea)
- **chunking** (`ingest.py`): swap fixed-size windows for sentence/semantic chunking — does `eval` improve?
- **hybrid search** (`store.py`): add BM25 keyword scores + reciprocal-rank fusion.
- **query construction** (`rag.py`): rewrite/route the query before retrieval.
- **more tools** (`agent/`): add a SQL or web-search tool with a guard.
- **production store**: pgvector instead of brute-force NumPy — *implemented* in
  `app/store_pg.py` (same interface, switched on by `DATABASE_URL`), with the schema
  owned by Alembic migrations in `alembic/`. See the README's pgvector section.

## Stage tags
`git checkout l03-chat | l05-index | l06-rag | l07-eval | l10-agent` to see the app at
each stage. `git diff l05-index l06-rag` is "what RAG adds".
