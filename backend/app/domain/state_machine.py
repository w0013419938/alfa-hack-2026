"""Машина состояний заявки — ЕДИНСТВЕННОЕ место, где меняется статус.

Таблица TRANSITIONS описывает все допустимые переходы:
    (из каких статусов, действие) → в какой статус, кто может выполнить, предусловие.

Любая смена статуса идёт через apply_transition():
- строка заявки блокируется (SELECT ... FOR UPDATE), поэтому два одновременных действия не «перетрут» друг друга;
- проверяются допустимость перехода, роль и предусловие;
- статус меняется и пишется ApplicationEvent — в одной транзакции (коммит делает вызывающий код).
Недопустимый переход → ConflictError (HTTP 409) с понятным сообщением.
"""

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_config import get_business_config
from app.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from app.domain.statuses import Actor, ApplicationStatus, EDITABLE_STATUSES
from app.models import Application, ApplicationEvent, Document, InfoRequest, Offer
from app.models.offer import OFFER_ACTIVE, OFFER_SUPERSEDED

logger = logging.getLogger(__name__)

S = ApplicationStatus


# ---------- Предусловия ----------
# Функция получает сессию и заявку и возвращает текст ошибки (почему нельзя) или None (можно).


def offer_is_active(db: Session, application: Application) -> str | None:
    offer = get_active_offer(db, application.id)
    if offer is None:
        return "По заявке нет действующего предложения."
    if offer.valid_until < datetime.now(UTC):
        return "Срок действия предложения истёк. Подайте новую заявку."
    return None


def requested_documents_uploaded(db: Session, application: Application) -> str | None:
    info_request = get_open_info_request(db, application.id)
    if info_request is None or not info_request.requested_documents:
        return None
    uploaded_kinds = set(
        db.scalars(
            select(Document.kind).where(
                Document.application_id == application.id,
                Document.created_at >= info_request.created_at,
            )
        )
    )
    missing = [kind for kind in info_request.requested_documents if kind not in uploaded_kinds]
    if not missing:
        return None
    dictionaries = get_business_config().dictionaries
    names = ", ".join(f"«{dictionaries.document_kind(kind).label if dictionaries.document_kind(kind) else kind}»" for kind in missing)
    return f"Сначала загрузите документы: {names}."


# ---------- Таблица переходов ----------


@dataclass(frozen=True)
class Transition:
    action: str
    from_statuses: tuple[ApplicationStatus, ...]
    to_status: ApplicationStatus
    actors: tuple[Actor, ...]
    precondition: Callable[[Session, Application], str | None] | None = None
    requires_comment: bool = False


TRANSITIONS: list[Transition] = [
    # --- Клиент ---
    Transition("submit", (S.DRAFT,), S.SUBMITTED, (Actor.CLIENT,)),
    Transition("provide_info", (S.NEEDS_INFO,), S.SUBMITTED, (Actor.CLIENT,), precondition=requested_documents_uploaded),
    Transition("accept_offer", (S.OFFER_SENT,), S.OFFER_ACCEPTED, (Actor.CLIENT,), precondition=offer_is_active),
    Transition("sign", (S.OFFER_ACCEPTED,), S.SIGNING, (Actor.CLIENT,)),
    Transition("decline_offer", (S.OFFER_SENT, S.OFFER_ACCEPTED), S.CLIENT_DECLINED, (Actor.CLIENT,)),
    Transition("cancel", (S.DRAFT, S.NEEDS_INFO, S.MANUAL_REVIEW), S.CANCELLED, (Actor.CLIENT,)),
    # --- Сотрудник банка (только из ручного рассмотрения, комментарий обязателен) ---
    Transition("approve", (S.MANUAL_REVIEW,), S.OFFER_SENT, (Actor.EMPLOYEE,), requires_comment=True),
    Transition("counter_offer", (S.MANUAL_REVIEW,), S.OFFER_SENT, (Actor.EMPLOYEE,), requires_comment=True),
    Transition("request_info", (S.MANUAL_REVIEW,), S.NEEDS_INFO, (Actor.EMPLOYEE,), requires_comment=True),
    Transition("reject", (S.MANUAL_REVIEW,), S.REJECTED, (Actor.EMPLOYEE,), requires_comment=True),
    # --- Система (пайплайн) ---
    Transition("start_validation", (S.SUBMITTED,), S.VALIDATION, (Actor.SYSTEM,)),
    Transition("validation_failed", (S.VALIDATION,), S.NEEDS_INFO, (Actor.SYSTEM,)),
    Transition("validation_passed", (S.VALIDATION,), S.CHECKS, (Actor.SYSTEM,)),
    Transition("checks_completed", (S.CHECKS,), S.SCORING, (Actor.SYSTEM,)),
    Transition("auto_approve", (S.SCORING,), S.OFFER_SENT, (Actor.SYSTEM,)),
    Transition("auto_counter_offer", (S.SCORING,), S.OFFER_SENT, (Actor.SYSTEM,)),
    Transition("auto_reject", (S.SCORING,), S.REJECTED, (Actor.SYSTEM,)),
    Transition("send_to_manual_review", (S.SCORING,), S.MANUAL_REVIEW, (Actor.SYSTEM,)),
    Transition("auto_request_info", (S.SCORING,), S.NEEDS_INFO, (Actor.SYSTEM,)),
    Transition("technical_error", (S.SUBMITTED, S.VALIDATION, S.CHECKS, S.SCORING), S.MANUAL_REVIEW, (Actor.SYSTEM,)),
    Transition("issue", (S.SIGNING,), S.ISSUED, (Actor.SYSTEM,)),
]

CLIENT_ACTIONS = ["submit", "cancel", "provide_info", "accept_offer", "decline_offer", "sign"]
EMPLOYEE_ACTIONS = ["approve", "counter_offer", "request_info", "reject"]

# Действия без смены статуса, которые тоже показываются кнопками
CLIENT_EDIT_ACTIONS = ["edit", "upload_document"]

# Статусы, в которые заявка попадает после окончательного решения банка (для статистики)
DECISION_STATUSES = {S.OFFER_SENT, S.REJECTED}


def find_transition(status: str, action: str) -> Transition | None:
    for transition in TRANSITIONS:
        if action == transition.action and status in transition.from_statuses:
            return transition
    return None


def action_exists(action: str) -> bool:
    return any(transition.action == action for transition in TRANSITIONS)


# ---------- Вспомогательные запросы ----------


def get_active_offer(db: Session, application_id: uuid.UUID) -> Offer | None:
    return db.scalar(
        select(Offer)
        .where(Offer.application_id == application_id, Offer.status == OFFER_ACTIVE)
        .order_by(Offer.created_at.desc())
        .limit(1)
    )


def get_current_offer(db: Session, application_id: uuid.UUID) -> Offer | None:
    """Последнее предложение, которое не было заменено новым (действующее, принятое или отклонённое)."""
    return db.scalar(
        select(Offer)
        .where(Offer.application_id == application_id, Offer.status != OFFER_SUPERSEDED)
        .order_by(Offer.created_at.desc())
        .limit(1)
    )


def get_open_info_request(db: Session, application_id: uuid.UUID) -> InfoRequest | None:
    return db.scalar(
        select(InfoRequest)
        .where(InfoRequest.application_id == application_id, InfoRequest.is_open.is_(True))
        .order_by(InfoRequest.created_at.desc())
        .limit(1)
    )


def lock_application(db: Session, application_id: uuid.UUID) -> Application:
    """Читает заявку с блокировкой строки до конца транзакции."""
    application = db.get(Application, application_id, with_for_update=True, populate_existing=True)
    if application is None:
        raise NotFoundError("Заявка не найдена")
    return application


# ---------- Главные функции ----------


def apply_transition(
    db: Session,
    application_id: uuid.UUID,
    action: str,
    actor: Actor,
    user_id: uuid.UUID | None = None,
    comment: str | None = None,
    payload: dict | None = None,
) -> tuple[Application, ApplicationEvent]:
    """Выполняет переход. Коммит транзакции — на стороне вызывающего кода."""
    labels = get_business_config().labels
    application = lock_application(db, application_id)
    current = application.status

    transition = find_transition(current, action)
    if transition is None:
        action_label = labels.actions[action].label if action in labels.actions else action
        raise ConflictError(
            f"Действие «{action_label}» сейчас недоступно: заявка в статусе «{labels.statuses[current].label}».",
            code="transition_not_allowed",
            details={"status": current, "action": action},
        )
    if actor not in transition.actors:
        raise ForbiddenError("У вас нет прав на это действие")
    if transition.requires_comment and not (comment and comment.strip()):
        raise AppError("Для этого действия нужен комментарий", code="comment_required")
    if transition.precondition:
        problem = transition.precondition(db, application)
        if problem:
            raise ConflictError(problem, code="precondition_failed")

    now = datetime.now(UTC)
    application.status = transition.to_status
    application.updated_at = now
    if transition.to_status == S.SUBMITTED and application.submitted_at is None:
        application.submitted_at = now
    if transition.to_status in DECISION_STATUSES and application.decided_at is None:
        application.decided_at = now

    event = ApplicationEvent(
        application_id=application.id,
        from_status=current,
        to_status=transition.to_status,
        action=action,
        actor_type=actor.value,
        actor_user_id=user_id,
        comment=comment,
        payload=payload or {},
        created_at=now,
    )
    db.add(event)
    db.flush()

    logger.info(
        "Смена статуса заявки",
        extra={
            "application_id": str(application.id),
            "action": action,
            "from_status": current,
            "to_status": transition.to_status.value,
            "actor": actor.value,
        },
    )
    return application, event


def record_creation(db: Session, application: Application, user_id: uuid.UUID) -> ApplicationEvent:
    """Первое событие истории: заявка создана (статус появляется впервые, поэтому from_status пустой)."""
    event = ApplicationEvent(
        application_id=application.id,
        from_status=None,
        to_status=S.DRAFT,
        action="create",
        actor_type=Actor.CLIENT.value,
        actor_user_id=user_id,
        payload={},
    )
    db.add(event)
    logger.info("Заявка создана", extra={"application_id": str(application.id), "to_status": S.DRAFT.value})
    return event


@dataclass
class AvailableAction:
    code: str
    enabled: bool = True
    disabled_reason: str | None = None
    requires_comment: bool = False


def available_actions(db: Session, application: Application, actor: Actor) -> list[AvailableAction]:
    """Какие кнопки показать пользователю с этой ролью прямо сейчас.

    Если действие есть, но предусловие не выполнено (например, не загружен документ),
    кнопка возвращается с enabled=False и причиной — фронт покажет её неактивной с подсказкой.
    """
    result: list[AvailableAction] = []
    if actor == Actor.CLIENT and application.status in EDITABLE_STATUSES:
        result.extend(AvailableAction(code=code) for code in CLIENT_EDIT_ACTIONS)

    for transition in TRANSITIONS:
        if actor not in transition.actors or application.status not in transition.from_statuses:
            continue
        problem = transition.precondition(db, application) if transition.precondition else None
        result.append(
            AvailableAction(
                code=transition.action,
                enabled=problem is None,
                disabled_reason=problem,
                requires_comment=transition.requires_comment,
            )
        )
    return result
