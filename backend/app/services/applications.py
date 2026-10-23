"""Заявки клиента: создание, редактирование, действия."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.business_config import get_business_config
from app.core.errors import AppError, ConflictError, NotFoundError
from app.domain.state_machine import (
    CLIENT_ACTIONS,
    apply_transition,
    get_active_offer,
    get_current_offer,
    get_open_info_request,
    lock_application,
    record_creation,
)
from app.domain.statuses import AUTOMATIC_STATUSES, EDITABLE_STATUSES, Actor, ApplicationStatus
from app.models import Application, ApplicationEvent, Product, User
from app.models.offer import OFFER_ACCEPTED, OFFER_DECLINED
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.services.contracts import save_signed_contract
from app.services.dispatcher import PipelineDispatcher

logger = logging.getLogger(__name__)

# После этих действий заявку снова обрабатывает система
ACTIONS_STARTING_PIPELINE = {"submit", "provide_info", "sign"}


def get_client_application(db: Session, user: User, application_id: uuid.UUID) -> Application:
    """Заявка, доступная клиенту. Чужая заявка выглядит как несуществующая (404), чтобы не раскрывать её наличие."""
    application = db.get(Application, application_id)
    if application is None or application.company_id != user.company_id:
        raise NotFoundError("Заявка не найдена")
    return application


def list_client_applications(db: Session, user: User, page: int, page_size: int) -> tuple[list[Application], int]:
    query = select(Application).where(Application.company_id == user.company_id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(Application.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return list(items), total or 0


def check_product_and_purpose(db: Session, product_code: str | None, purpose_code: str | None) -> None:
    if product_code is not None:
        product = db.get(Product, product_code)
        if product is None or not product.is_active:
            raise AppError("Такого кредитного продукта нет. Выберите продукт из списка.", code="unknown_product")
    if purpose_code is not None and get_business_config().dictionaries.purpose(purpose_code) is None:
        raise AppError("Такой цели кредита нет. Выберите цель из списка.", code="unknown_purpose")


def check_version(application: Application, expected_version: int | None) -> None:
    if expected_version is not None and expected_version != application.version:
        raise ConflictError(
            "Заявку только что изменили. Обновите страницу и повторите действие.",
            code="version_conflict",
            details={"current_version": application.version},
        )


def create_draft(db: Session, user: User, data: ApplicationCreate) -> Application:
    check_product_and_purpose(db, data.product_code, data.purpose_code)
    application = Application(
        company_id=user.company_id,
        author_id=user.id,
        status=ApplicationStatus.DRAFT,
        **data.model_dump(),
    )
    db.add(application)
    db.flush()
    record_creation(db, application, user.id)
    db.commit()
    return application


def update_draft(db: Session, user: User, application_id: uuid.UUID, data: ApplicationUpdate) -> Application:
    get_client_application(db, user, application_id)  # проверка доступа
    application = lock_application(db, application_id)
    check_version(application, data.version)
    if application.status not in EDITABLE_STATUSES:
        status_label = get_business_config().status_label(application.status)
        raise ConflictError(f"Заявку в статусе «{status_label}» менять нельзя.", code="not_editable")

    changes = data.model_dump(exclude_unset=True, exclude={"version"})
    check_product_and_purpose(db, changes.get("product_code"), changes.get("purpose_code"))
    if "product_code" in changes and changes["product_code"] is None:
        raise AppError("Продукт нельзя убрать из заявки — выберите другой продукт.", code="unknown_product")
    for field, value in changes.items():
        setattr(application, field, value)
    application.updated_at = datetime.now(UTC)
    db.commit()
    return application


def is_repeat_of_last_action(db: Session, application_id: uuid.UUID, action: str, user_id: uuid.UUID) -> bool:
    """Повтор того же действия тем же пользователем (двойной клик, повтор запроса после обрыва связи).

    Считаем запрос повтором, только если:
    - последнее действие человека по заявке — это же действие этого же пользователя;
    - заявка всё ещё в статусе, куда её привело это действие, или в автоматической обработке после него.
    Если процесс уже дошёл до нового решения (например, NEEDS_INFO или OFFER_SENT), повтор — это новая попытка,
    и она получает обычный 409.
    """
    last_human_event = db.scalar(
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application_id, ApplicationEvent.actor_type != Actor.SYSTEM.value)
        .order_by(ApplicationEvent.created_at.desc())
        .limit(1)
    )
    if last_human_event is None or last_human_event.action != action or last_human_event.actor_user_id != user_id:
        return False
    current_status = db.scalar(select(Application.status).where(Application.id == application_id))
    return current_status == last_human_event.to_status or current_status in AUTOMATIC_STATUSES


def perform_client_action(
    db: Session,
    user: User,
    application_id: uuid.UUID,
    action: str,
    comment: str | None,
    expected_version: int | None,
    dispatcher: PipelineDispatcher,
) -> Application:
    if action not in CLIENT_ACTIONS:
        raise NotFoundError(f"Неизвестное действие «{action}». Доступные действия: {', '.join(CLIENT_ACTIONS)}.", code="unknown_action")
    get_client_application(db, user, application_id)  # проверка доступа

    try:
        application = lock_application(db, application_id)
        check_version(application, expected_version)
        application, _ = apply_transition(db, application_id, action, Actor.CLIENT, user_id=user.id, comment=comment)
        apply_client_side_effects(db, application, action, comment, user)
        db.commit()
    except ConflictError as error:
        db.rollback()
        # Идемпотентность: повтор уже выполненного действия возвращает текущее состояние, а не ошибку
        if error.code == "transition_not_allowed" and is_repeat_of_last_action(db, application_id, action, user.id):
            logger.info("Повтор действия — возвращаем текущее состояние", extra={"application_id": str(application_id), "action": action})
            return db.get(Application, application_id, populate_existing=True)
        raise

    if action in ACTIONS_STARTING_PIPELINE:
        dispatcher.dispatch(application.id)
    return application


def apply_client_side_effects(db: Session, application: Application, action: str, comment: str | None, user: User) -> None:
    """Что ещё меняется вместе со статусом (в той же транзакции)."""
    if action == "provide_info":
        info_request = get_open_info_request(db, application.id)
        if info_request:
            info_request.is_open = False
            info_request.response_comment = comment
            info_request.responded_at = datetime.now(UTC)
    elif action == "accept_offer":
        get_active_offer(db, application.id).status = OFFER_ACCEPTED
    elif action == "decline_offer":
        # Отказаться можно и от действующего, и от уже принятого (но не подписанного) предложения
        offer = get_current_offer(db, application.id)
        if offer:
            offer.status = OFFER_DECLINED
    elif action == "sign":
        save_signed_contract(db, application, user)
