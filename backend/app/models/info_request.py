import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, uuid_pk


class InfoRequest(Base):
    """Запрос уточнений: что банк просит исправить или донести."""

    __tablename__ = "info_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    # Поля анкеты, которые нужно исправить: [{"field": "amount", "message": "..."}]
    requested_fields: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Коды видов документов, которые нужно загрузить: ["bank_statement"]
    requested_documents: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_type: Mapped[str] = mapped_column(String(16), nullable=False)  # system / employee
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    response_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
