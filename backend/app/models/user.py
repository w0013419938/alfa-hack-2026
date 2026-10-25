import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_column, uuid_pk
from app.models.company import Company

ROLE_CLIENT = "client"
ROLE_EMPLOYEE = "employee"


class User(Base):
    """Пользователь: представитель компании (client) или сотрудник банка (employee)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    login: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    company_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    # Должность в компании (owner, director, accountant ...), коды из config/dictionaries.yaml
    position: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = created_at_column()

    company: Mapped[Company | None] = relationship()
