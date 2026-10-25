import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Identity, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_column, utc_now, uuid_pk
from app.models.company import Company
from app.models.product import Product
from app.models.user import User


class Application(Base):
    """Заявка на кредит.

    Статус меняется ТОЛЬКО через app/domain/state_machine.py.
    Поле version нужно для оптимистичной блокировки: SQLAlchemy сам увеличивает его при каждом UPDATE
    и выдаёт ошибку, если строку уже успели изменить в другом месте.
    """

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = uuid_pk()
    # Короткий понятный номер заявки для людей («Заявка № 1001»)
    number: Mapped[int] = mapped_column(Integer, Identity(start=1001), unique=True, nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_code: Mapped[str] = mapped_column(ForeignKey("products.code"), nullable=False)

    # Параметры кредита (в черновике могут быть не заполнены)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    term_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purpose_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    purpose_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    collateral_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Финансовые данные из анкеты, в рублях в месяц
    monthly_revenue: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    monthly_expenses: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    current_loan_payments: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped[Company] = relationship()
    author: Mapped[User] = relationship()
    product: Mapped[Product] = relationship()

    __mapper_args__ = {"version_id_col": version}


class ApplicationEvent(Base):
    """Событие истории заявки: смена статуса. Это и аудит, и таймлайн для клиента."""

    __tablename__ = "application_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)  # None, если заявка только создана
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)  # client / employee / system
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Комментарий виден клиенту в таймлайне
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Технические подробности (причины решения, ошибки интеграций), видит только сотрудник
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = created_at_column()
