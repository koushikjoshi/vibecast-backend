from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def _ensure_dirs(settings) -> None:
    db_path = Path(settings.db_path)
    if db_path.parent:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    Path(settings.projects_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)


_settings = get_settings()
_ensure_dirs(_settings)

engine = create_engine(
    _settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    # Import models so their metadata is registered before create_all.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)

    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        conn.exec_driver_sql("PRAGMA busy_timeout=5000;")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
