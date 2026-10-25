import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, uuid_pk


class Company(Base):
    """Компания клиента (ООО или ИП)."""

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = uuid_pk()
    inn: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    ogrn: Mapped[str] = mapped_column(String(15), nullable=False)  # ОГРН (13 цифр) или ОГРНИП (15 цифр)
    company_type: Mapped[str] = mapped_column(String(8), nullable=False)  # LLC (ООО) или IE (ИП)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    okved: Mapped[str] = mapped_column(String(16), nullable=False)  # основной ОКВЭД, например "47.11"
    industry: Mapped[str] = mapped_column(String(255), nullable=False)  # отрасль простыми словами
    registration_date: Mapped[date] = mapped_column(Date, nullable=False)
    region: Mapped[str] = mapped_column(String(255), nullable=False)
    # Выручка за последний год по отчётности. None значит, что отчётности ещё нет (например, у нового ИП).
    annual_revenue: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    employees_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = created_at_column()
