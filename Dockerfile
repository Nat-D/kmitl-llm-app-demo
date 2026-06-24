FROM python:3.12-slim

# uv for fast, reproducible installs (same tool the course uses).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# Corpus index lives in a writable path; rebuilt at startup (it's tiny).
ENV DB_PATH=/tmp/store.db PYTHONUNBUFFERED=1
EXPOSE 8000

# Embed the corpus, then serve. Needs OPENAI_BASE_URL / OPENAI_API_KEY in the env.
CMD ["sh", "-c", "uv run python -m app.ingest corpus && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
