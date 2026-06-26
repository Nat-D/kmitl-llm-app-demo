"""create the chunks table with a pgvector embedding column

This is the production way to create the schema — `alembic upgrade head` runs it.
(The app also CREATE TABLE IF NOT EXISTS so the demo works without it, but in a real
backend migrations own the schema: each change is a new, reviewable, ordered revision
you can roll forward and back, instead of editing tables by hand.)

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

DIM = 1024  # bge-m3 embedding dimensions


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        f"CREATE TABLE IF NOT EXISTS chunks ("
        f"id serial PRIMARY KEY, title text, text text, embedding vector({DIM}))"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chunks")
