"""Pick the vector-store backend ONCE, here, so the rest of the app doesn't care
which one it's talking to.

- default: the SQLite + NumPy store in `store.py` (zero setup, easy to read).
- if DATABASE_URL is set: the pgvector store in `store_pg.py` (the production swap).

Both modules expose the same names (Hit / connect / add / search / count), so every
caller just does `from app.vectorstore import store` and uses `store.search(...)`.
"""
import os

if os.environ.get("DATABASE_URL"):
    from app import store_pg as store  # noqa: F401  (re-exported)
else:
    from app import store  # noqa: F401  (re-exported)
