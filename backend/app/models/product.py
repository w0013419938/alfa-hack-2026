from decimal import Decimal

from sqlalchemy import JSON, Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Product(Base):
    """Кредитный продукт. Источник истины — config/products.yaml, таблица обновляется при каждом старте."""

    __tablename__ = "products"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suitable_for: Mapped[str] = mapped_column(Text, nullable=False)
    purposes: Mapped[list] = mapped_column(JSON, nullable=False)  # коды целей из dictionaries.yaml
    min_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    max_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    min_term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    max_term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    base_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # % годовых
    requires_collateral: Mapped[bool] = mapped_column(Boolean, nullable=False)
    decision_days: Mapped[int] = mapped_column(Integer, nullable=False)  # за сколько дней обычно решение
    required_fields: Mapped[list] = mapped_column(JSON, nullable=False)  # обязательные поля заявки
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
