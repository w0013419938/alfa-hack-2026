import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, uuid_pk

CHECK_EGRUL = "egrul"
CHECK_BKI = "bki"

CHECK_OK = "ok"
CHECK_ERROR = "error"
CHECK_TIMEOUT = "timeout"


class ExternalCheck(Base):
    """Запрос во внешний источник (ЕГРЮЛ/ЕГРИП или БКИ) и его результат."""

    __tablename__ = "external_checks"

    id: Mapped[uuid.UUID] = uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    check_type: Mapped[str] = mapped_column(String(16), nullable=False)  # egrul / bki
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # ok / error / timeout
    request: Mapped[dict] = mapped_column(JSON, nullable=False)
    response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = created_at_column()


class ScoringResult(Base):
    """Результат скоринга: балл, грейд и вклад каждого фактора (для объяснимости)."""

    __tablename__ = "scoring_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(4), nullable=False, index=True)
    # Список факторов: [{code, name, value, points, max_points, explanation}]
    factors: Mapped[list] = mapped_column(JSON, nullable=False)
    debt_to_income: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    rules_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = created_at_column()
