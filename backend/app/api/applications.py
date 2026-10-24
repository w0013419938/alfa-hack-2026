"""Эндпоинты клиента: моя компания, мои заявки, действия, документы."""

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_client
from app.core.db import get_db
from app.domain.statuses import Actor
from app.models import Document, User
from app.schemas.application import ApplicationCreate, ApplicationOut, ApplicationUpdate, ClientActionRequest
from app.schemas.common import Page
from app.schemas.company import CompanyOut, DocumentOut
from app.services import applications as service
from app.services.contracts import CONTRACT_KIND, render_contract
from app.services.dispatcher import PipelineDispatcher, get_dispatcher
from app.services.documents import document_file_path, get_document, list_documents, save_upload
from app.services.presenters import build_application_out, build_company, build_document

router = APIRouter(tags=["Клиент: заявки"])


@router.get("/company", response_model=CompanyOut, summary="Моя компания")
def my_company(user: User = Depends(get_current_client)):
    return build_company(user.company)


@router.get("/applications", response_model=Page[ApplicationOut], summary="Мои заявки")
def list_applications(
    page: int = Query(1, ge=1, le=100_000),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    items, total = service.list_client_applications(db, user, page, page_size)
    return Page(
        items=[build_application_out(db, item, Actor.CLIENT) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/applications", response_model=ApplicationOut, status_code=201, summary="Создать черновик заявки")
def create_application(body: ApplicationCreate, user: User = Depends(get_current_client), db: Session = Depends(get_db)):
    application = service.create_draft(db, user, body)
    return build_application_out(db, application, Actor.CLIENT)


@router.get("/applications/{application_id}", response_model=ApplicationOut, summary="Заявка")
def get_application(application_id: uuid.UUID, user: User = Depends(get_current_client), db: Session = Depends(get_db)):
    application = service.get_client_application(db, user, application_id)
    return build_application_out(db, application, Actor.CLIENT)


@router.patch(
    "/applications/{application_id}",
    response_model=ApplicationOut,
    summary="Изменить черновик (или заявку в статусе «Нужны уточнения»)",
)
def update_application(
    application_id: uuid.UUID,
    body: ApplicationUpdate,
    user: User = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    application = service.update_draft(db, user, application_id, body)
    return build_application_out(db, application, Actor.CLIENT)


@router.post(
    "/applications/{application_id}/actions/{action}",
    response_model=ApplicationOut,
    summary="Действие клиента: submit, cancel, provide_info, accept_offer, decline_offer, sign",
    description=(
        "Единая точка для действий над заявкой. Какие действия доступны сейчас, видно в `available_actions`. "
        "Повтор уже выполненного действия (двойной клик) не ломает заявку: вернётся её текущее состояние."
    ),
)
def client_action(
    application_id: uuid.UUID,
    action: str,
    body: ClientActionRequest | None = None,
    user: User = Depends(get_current_client),
    db: Session = Depends(get_db),
    dispatcher: PipelineDispatcher = Depends(get_dispatcher),
):
    body = body or ClientActionRequest()
    application = service.perform_client_action(db, user, application_id, action, body.comment, body.version, dispatcher)
    return build_application_out(db, application, Actor.CLIENT)


@router.get("/applications/{application_id}/documents", response_model=list[DocumentOut], summary="Документы заявки")
def get_documents(application_id: uuid.UUID, user: User = Depends(get_current_client), db: Session = Depends(get_db)):
    service.get_client_application(db, user, application_id)
    return [build_document(item, Actor.CLIENT) for item in list_documents(db, application_id)]


@router.post(
    "/applications/{application_id}/documents",
    response_model=DocumentOut,
    status_code=201,
    summary="Загрузить документ (PDF, JPG, PNG до 10 МБ)",
    description="Загружать можно в статусах «Черновик» и «Нужны уточнения». Вид документа указывается кодом из `/dictionaries/document-kinds`.",
)
def upload_document(
    application_id: uuid.UUID,
    kind: str = Form(description="Код вида документа, например bank_statement"),
    file: UploadFile = File(description="Файл PDF, JPG или PNG"),
    user: User = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    application = service.get_client_application(db, user, application_id)
    document = save_upload(db, application, user, kind, file)
    return build_document(document, Actor.CLIENT)


@router.get("/applications/{application_id}/documents/{document_id}/download", summary="Скачать документ")
def download_document(
    application_id: uuid.UUID,
    document_id: uuid.UUID,
    user: User = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    service.get_client_application(db, user, application_id)
    document = get_document(db, application_id, document_id)
    return FileResponse(document_file_path(document), media_type=document.content_type, filename=document.original_filename)


@router.get(
    "/applications/{application_id}/contract",
    response_class=HTMLResponse,
    summary="Кредитный договор (HTML)",
    description="До подписания отдаёт проект договора по текущему предложению, после подписания подписанную версию.",
)
def get_contract(application_id: uuid.UUID, user: User = Depends(get_current_client), db: Session = Depends(get_db)):
    application = service.get_client_application(db, user, application_id)
    signed = db.scalar(
        select(Document)
        .where(Document.application_id == application_id, Document.kind == CONTRACT_KIND)
        .order_by(Document.created_at.desc())
        .limit(1)
    )
    if signed:
        return HTMLResponse(document_file_path(signed).read_text(encoding="utf-8"))
    return HTMLResponse(render_contract(db, application, user, signed_at=None))
