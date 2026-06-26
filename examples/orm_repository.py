"""The data layer the mini app deliberately skips — an ORM model + a repository.

The app itself uses raw SQL in store.py for readability. But the "house style" for a
growing backend is router -> service -> REPOSITORY, and the repository is usually
built on an ORM so rows are typed objects and queries compose. This file shows that
bottom layer on its own, runnable over in-memory SQLite (zero setup).

It pairs with alembic/: in production a MIGRATION creates the `conversations` table,
and this ORM model maps to it. (The app is async; this example uses sync SQLAlchemy to
stay dependency-light — the shape is identical.)

Run it (needs SQLAlchemy from the pg group):
    uv run --group pg python -m examples.orm_repository
"""
from datetime import datetime

from sqlalchemy import String, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    """One stored chat turn. An Alembic migration owns this table in production."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str]
    reply: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ConversationRepository:
    """Pure data access — NO business logic. One class per aggregate. The service
    calls these methods; the router never touches the database."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, user_id: str, message: str, reply: str) -> Conversation:
        turn = Conversation(user_id=user_id, message=message, reply=reply)
        self._session.add(turn)
        self._session.flush()
        return turn

    def recent(self, user_id: str, limit: int = 5) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.id.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))


if __name__ == "__main__":
    # In-memory SQLite so this runs with zero setup. In production you'd point the
    # engine at Postgres via DATABASE_URL, and the schema would come from a migration
    # (alembic upgrade head) instead of create_all().
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = ConversationRepository(session)
        repo.add("u1", "what is RAG?", "Retrieval-augmented generation grounds answers.")
        repo.add("u1", "and embeddings?", "Vectors that place similar text close together.")
        session.commit()
        for turn in repo.recent("u1"):
            print(f"[{turn.id}] {turn.user_id}: {turn.message!r} -> {turn.reply[:32]!r}")
