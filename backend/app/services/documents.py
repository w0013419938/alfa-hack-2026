"""Документы заявки: проверка и сохранение файлов.

Файлы лежат на диске в UPLOAD_DIR/<id заявки>/<случайное имя>, в БД — только метаданные.
Имя файла на диске генерируется нами, поэтому имя от пользователя не может «выйти» из папки.
"""

import logging
import re
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.business_config import get_business_config
from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.settings import get_settings
from app.domain.state_machine import lock_application
from app.domain.statuses import EDITABLE_STATUSES
from app.models import Application, Document, User

logger = logging.getLogger(__name__)

# Сигнатуры (первые байты) файлов: проверяем, что содержимое соответствует расширению
FILE_SIGNATURES = {
    ".pdf": [b"%PDF"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
}
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".html": "text/html; charset=utf-8",
}
UNSAFE_CHARS = re.compile(r"[^\w.\- ]", re.UNICODE)


def safe_filename(name: str | None) -> str:
    """Оставляет от имени файла только безопасные символы: буквы, цифры, точку, дефис, пробел, подчёркивание."""
    base = Path(name or "").name  # отбрасываем путь вроде ../../etc/passwd
    cleaned = UNSAFE_CHARS.sub("_", base).strip(" .")
    return cleaned[:100] or "document"


def store_bytes(application_id: uuid.UUID, content: bytes, extension: str) -> str:
    """Сохраняет файл и возвращает путь относительно UPLOAD_DIR."""
    relative = Path(str(application_id)) / f"{uuid.uuid4().hex}{extension}"
    full_path = get_settings().upload_dir / relative
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(content)
    return str(relative)


def document_file_path(document: Document) -> Path:
    upload_dir = get_settings().upload_dir.resolve()
    path = (upload_dir / document.stored_path).resolve()
    if not path.is_relative_to(upload_dir) or not path.exists():
        raise NotFoundError("Файл документа не найден")
    return path


def save_upload(db: Session, application: Application, user: User, kind: str, upload: UploadFile) -> Document:
    settings = get_settings()
    config = get_business_config()

    if application.status not in EDITABLE_STATUSES:
        status_label = config.status_label(application.status)
        raise ConflictError(f"В статусе «{status_label}» документы загружать нельзя.", code="not_editable")

    kind_config = config.dictionaries.document_kind(kind)
    if kind_config is None:
        raise AppError("Неизвестный вид документа. Выберите вид из списка.", code="unknown_document_kind")
    if not kind_config.client_can_upload:
        raise AppError(f"Документ «{kind_config.label}» формирует банк, загрузить его нельзя.", code="document_kind_not_uploadable")

    # Блокируем заявку, чтобы параллельные загрузки не обошли лимит количества документов
    lock_application(db, application.id)
    documents_count = db.scalar(select(func.count()).select_from(Document).where(Document.application_id == application.id))
    if documents_count >= settings.max_documents_per_application:
        raise AppError(
            f"К заявке можно приложить не больше {settings.max_documents_per_application} документов.",
            code="too_many_documents",
        )

    filename = safe_filename(upload.filename)
    extension = Path(filename).suffix.lower()
    if extension not in settings.allowed_extension_list:
        allowed = ", ".join(item.lstrip(".").upper() for item in settings.allowed_extension_list)
        raise AppError(f"Этот тип файла не поддерживается. Можно загрузить: {allowed}.", code="file_type_not_allowed")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = upload.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise AppError(f"Файл слишком большой. Максимальный размер — {settings.max_upload_mb} МБ.", code="file_too_large")
    if not content:
        raise AppError("Файл пустой.", code="file_empty")
    signatures = FILE_SIGNATURES.get(extension, [])
    if signatures and not any(content.startswith(signature) for signature in signatures):
        raise AppError("Содержимое файла не соответствует его расширению.", code="file_content_mismatch")

    document = Document(
        application_id=application.id,
        uploaded_by_user_id=user.id,
        kind=kind,
        original_filename=filename,
        stored_path=store_bytes(application.id, content, extension),
        content_type=CONTENT_TYPES.get(extension, "application/octet-stream"),
        size_bytes=len(content),
    )
    db.add(document)
    db.commit()
    logger.info("Документ загружен", extra={"application_id": str(application.id)})
    return document


def list_documents(db: Session, application_id: uuid.UUID) -> list[Document]:
    return list(db.scalars(select(Document).where(Document.application_id == application_id).order_by(Document.created_at)))


def get_document(db: Session, application_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.application_id != application_id:
        raise NotFoundError("Документ не найден")
    return document
