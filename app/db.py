from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_session_local: sessionmaker[Session] | None = None


def configure_database(database_url: str | None = None) -> None:
    global _engine, _session_local
    url = database_url or get_settings().database_url
    if url.startswith("sqlite") and ":///" in url:
        sqlite_path = url.split(":///", 1)[1]
        if sqlite_path != ":memory:":
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, connect_args=connect_args, future=True)
    _session_local = sessionmaker(_engine, autoflush=False, autocommit=False, future=True)


def get_engine():
    if _engine is None:
        configure_database()
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    if _session_local is None:
        configure_database()
    return _session_local


def get_session() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
