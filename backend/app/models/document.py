import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, uuid_pk


class Document(Base):
    """Файл, приложенный к заявке. Сам файл лежит на диске (volume), в БД — только метаданные."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # None — система
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # код вида документа из dictionaries.yaml
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)  # уже очищенное имя
    stored_path: Mapped[str] = mapped_column(String(512), nullable=False)  # путь внутри UPLOAD_DIR
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = created_at_column()
