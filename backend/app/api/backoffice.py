"""Эндпоинты сотрудника банка (бэкофис). Доступны только роли employee."""

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.core.business_config import get_business_config
from app.core.db import get_db
from app.core.errors import AppError
from app.domain.statuses import ApplicationStatus
from app.models import User
from app.schemas.backoffice import BackofficeApplicationOut, BackofficeListItem, EmployeeActionRequest, StatsOut
from app.schemas.common import Page
from app.services import backoffice as service
from app.services.documents import document_file_path, get_document
from app.services.stats import get_stats

router = APIRouter(prefix="/backoffice", tags=["Сотрудник банка"])


@router.get("/applications", response_model=Page[BackofficeListItem], summary="Очередь заявок с фильтрами")
def list_applications(
    status: list[str] = Query(default_factory=list, description="Статусы (можно несколько: ?status=MANUAL_REVIEW&status=OFFER_SENT)"),
    product: str | None = Query(None, description="Код продукта"),
    grade: str | None = Query(None, description="Грейд риска (A–E)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    known_statuses = {item.value for item in ApplicationStatus}
    unknown = [item for item in status if item not in known_statuses]
    if unknown:
        raise AppError(f"Неизвестный статус: {', '.join(unknown)}.", code="unknown_status")
    if grade and grade not in {item.grade for item in get_business_config().scoring.grades}:
        raise AppError(f"Неизвестный грейд: {grade}.", code="unknown_grade")
    items, total = service.list_queue(db, status, product, grade, page, page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/applications/{application_id}",
    response_model=BackofficeApplicationOut,
    summary="Полная карточка заявки: анкета, компания, проверки, скоринг, история",
)
def get_application(application_id: uuid.UUID, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    return service.build_card(db, service.get_application(db, application_id))


@router.post(
    "/applications/{application_id}/actions/{action}",
    response_model=BackofficeApplicationOut,
    summary="Решение сотрудника: approve, counter_offer, request_info, reject",
    description="Доступно, когда заявка в статусе MANUAL_REVIEW. Комментарий обязателен — его увидит клиент.",
)
def employee_action(
    application_id: uuid.UUID,
    action: str,
    body: EmployeeActionRequest,
    user: User = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    application = service.perform_employee_action(db, user, application_id, action, body)
    return service.build_card(db, application)


@router.get("/applications/{application_id}/documents/{document_id}/download", summary="Скачать документ заявки")
def download_document(
    application_id: uuid.UUID,
    document_id: uuid.UUID,
    user: User = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    service.get_application(db, application_id)
    document = get_document(db, application_id, document_id)
    return FileResponse(document_file_path(document), media_type=document.content_type, filename=document.original_filename)


@router.get("/stats", response_model=StatsOut, summary="Метрики: заявки по статусам, доля автоодобрений, среднее время обработки")
def stats(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    return get_stats(db)
