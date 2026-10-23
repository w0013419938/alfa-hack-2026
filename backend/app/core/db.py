"""Подключение к базе данных (синхронный SQLAlchemy)."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings

# hide_parameters: в тексте ошибок SQL не будет значений (сумм, комментариев клиентов) — они не попадут в логи
engine = create_engine(get_settings().database_url, pool_pre_ping=True, pool_size=10, max_overflow=10, hide_parameters=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Зависимость FastAPI: одна сессия на запрос."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
