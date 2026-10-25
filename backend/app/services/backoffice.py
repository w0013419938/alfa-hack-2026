"""Рабочее место сотрудника банка: очередь, карточка заявки, решения по ручному рассмотрению."""

import logging
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.business_config import get_business_config
from app.core.errors import AppError, ConflictError, NotFoundError
from app.domain.decision import OfferTerms, offer_rate
from app.domain.formatting import format_money
from app.domain.payments import annuity_payment
from app.domain.state_machine import EMPLOYEE_ACTIONS, apply_transition, ensure_transition_allowed, lock_application
from app.domain.statuses import FINAL_STATUSES, Actor
from app.models import Application, ApplicationEvent, ExternalCheck, InfoRequest, Offer, ScoringResult, User
from app.models.checks import CHECK_BKI, CHECK_EGRUL, CHECK_OK
from app.models.offer import OFFER_AS_REQUESTED, OFFER_COUNTER
from app.schemas.backoffice import (
    AuthorOut,
    BackofficeApplicationOut,
    BackofficeListItem,
    CheckOut,
    DecisionOut,
    DecisionReasonOut,
    EmployeeActionRequest,
    EventOut,
    FactorOut,
    ScoringOut,
    SuggestedOffer,
)
from app.services.applications import check_version, is_repeat_of_last_action
from app.services.documents import list_documents
from app.services.offers import create_info_request, create_offer
from app.services.presenters import (
    actor_label,
    build_actions,
    build_application_out,
    build_company,
    build_document,
    build_info_request,
    build_offer,
    build_timeline,
    status_texts,
)

logger = logging.getLogger(__name__)

# Действия пайплайна, в которых система принимает первичное решение по заявке
DECISION_ACTIONS = {"auto_approve", "auto_counter_offer", "auto_reject", "send_to_manual_review", "auto_request_info"}


def latest_scoring(db: Session, application_id: uuid.UUID) -> ScoringResult | None:
    return db.scalar(
        select(ScoringResult).where(ScoringResult.application_id == application_id).order_by(ScoringResult.created_at.desc()).limit(1)
    )


def latest_grade_subquery():
    return (
        select(ScoringResult.grade)
        .where(ScoringResult.application_id == Application.id)
        .order_by(ScoringResult.created_at.desc())
        .limit(1)
        .scalar_subquery()
    )


# ---------- Очередь ----------


def list_queue(
    db: Session,
    statuses: list[str],
    product_code: str | None,
    grade: str | None,
    page: int,
    page_size: int,
) -> tuple[list[BackofficeListItem], int]:
    query = select(Application)
    if statuses:
        query = query.where(Application.status.in_(statuses))
    if product_code:
        query = query.where(Application.product_code == product_code)
    if grade:
        query = query.where(latest_grade_subquery() == grade)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    applications = db.scalars(query.order_by(Application.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()

    items = []
    for application in applications:
        scoring = latest_scoring(db, application.id)
        status_label, status_description = status_texts(application, Actor.EMPLOYEE)
        items.append(
            BackofficeListItem(
                id=application.id,
                number=application.number,
                company_name=application.company.name,
                company_inn=application.company.inn,
                product={"code": application.product.code, "name": application.product.name},
                amount=application.amount,
                term_months=application.term_months,
                status=application.status,
                status_label=status_label,
                status_description=status_description,
                is_final=application.status in FINAL_STATUSES,
                grade=scoring.grade if scoring else None,
                score=scoring.total_score if scoring else None,
                created_at=application.created_at,
                updated_at=application.updated_at,
                submitted_at=application.submitted_at,
                available_actions=build_actions(db, application, Actor.EMPLOYEE),
                timeline=build_timeline(db, application, Actor.EMPLOYEE),
            )
        )
    return items, total


# ---------- Карточка заявки ----------


def get_application(db: Session, application_id: uuid.UUID) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise NotFoundError("Заявка не найдена")
    return application


def check_summary(check: ExternalCheck, company_status_labels: dict[str, str]) -> list[str]:
    """Главное из ответа внешнего сервиса — коротко, чтобы сотруднику не читать JSON."""
    data = check.response or {}
    if check.status != CHECK_OK:
        return [f"Сервис не ответил: {check.error_message} (попыток: {check.attempts})"]
    if check.check_type == CHECK_EGRUL:
        if data.get("not_found"):
            return ["Компания не найдена в реестре"]
        director = (data.get("director") or {}).get("full_name", "—")
        return [
            f"Статус: {company_status_labels.get(data.get('status'), data.get('status'))}",
            f"Дата регистрации: {data.get('registration_date', '—')}",
            f"Основной ОКВЭД: {data.get('okved', '—')}",
            f"Руководитель: {director}",
        ]
    if check.check_type == CHECK_BKI:
        loans = data.get("active_loans") or []
        payments = sum(loan.get("monthly_payment", 0) for loan in loans)
        current_overdue = max((loan.get("current_overdue_days", 0) for loan in loans), default=0)
        history = data.get("overdue_history") or {}
        return [
            f"Кредитный рейтинг бюро: {data.get('rating', '—')}",
            f"Действующих кредитов: {len(loans)}, платежи {format_money(payments)} ₽ в месяц",
            f"Текущая просрочка: {current_overdue} дн." if current_overdue else "Текущей просрочки нет",
            f"Просрочек в истории: {history.get('count', 0)}, самая долгая {history.get('max_days', 0)} дн.",
        ]
    return []


def build_checks(db: Session, application_id: uuid.UUID) -> list[CheckOut]:
    labels = get_business_config().labels
    checks = db.scalars(select(ExternalCheck).where(ExternalCheck.application_id == application_id).order_by(ExternalCheck.created_at.desc()))
    return [
        CheckOut(
            id=check.id,
            check_type=check.check_type,
            check_type_label=labels.check_types.get(check.check_type, check.check_type),
            status=check.status,
            status_label=labels.check_statuses.get(check.status, check.status),
            attempts=check.attempts,
            duration_ms=check.duration_ms,
            error_message=check.error_message,
            summary=check_summary(check, labels.company_statuses),
            response=check.response,
            created_at=check.created_at,
        )
        for check in checks
    ]


def build_scoring(scoring: ScoringResult | None) -> ScoringOut | None:
    if scoring is None:
        return None
    grade_labels = {item.grade: item.label for item in get_business_config().scoring.grades}
    return ScoringOut(
        total_score=scoring.total_score,
        max_score=scoring.max_score,
        grade=scoring.grade,
        grade_label=grade_labels.get(scoring.grade, scoring.grade),
        debt_to_income=float(scoring.debt_to_income) if scoring.debt_to_income is not None else None,
        rules_version=scoring.rules_version,
        factors=[FactorOut(**factor) for factor in scoring.factors],
        created_at=scoring.created_at,
    )


def build_decision(db: Session, application_id: uuid.UUID) -> DecisionOut | None:
    event = db.scalar(
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application_id, ApplicationEvent.action.in_(DECISION_ACTIONS))
        .order_by(ApplicationEvent.created_at.desc())
        .limit(1)
    )
    if event is None or "decision" not in event.payload:
        return None
    outcomes = get_business_config().labels.decision_outcomes
    return DecisionOut(
        outcome=event.payload["decision"],
        outcome_label=outcomes.get(event.payload["decision"], event.payload["decision"]),
        reasons=[DecisionReasonOut(**reason) for reason in event.payload.get("reasons", [])],
        decided_at=event.created_at,
    )


def grade_for_offer(scoring: ScoringResult | None) -> str:
    """Грейд для расчёта ставки: из скоринга, а если скоринга нет — грейд по умолчанию из decision.yaml."""
    return scoring.grade if scoring else get_business_config().decision.manual_review_default_grade


def default_offer_terms(application: Application, scoring: ScoringResult | None) -> OfferTerms | None:
    """Условия, которые сотрудник видит в форме «Одобрить» по умолчанию: запрошенные сумма и срок, ставка по грейду."""
    if application.amount is None or application.term_months is None:
        return None
    rate = offer_rate(application.product.base_rate, grade_for_offer(scoring), get_business_config().decision)
    payment = annuity_payment(application.amount, rate, application.term_months)
    return OfferTerms(OFFER_AS_REQUESTED, Decimal(application.amount), application.term_months, rate, payment)


def build_events(db: Session, application_id: uuid.UUID) -> list[EventOut]:
    labels = get_business_config().labels
    events = db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id == application_id).order_by(ApplicationEvent.created_at))
    result = []
    for event in events:
        actor_name = db.get(User, event.actor_user_id).full_name if event.actor_user_id else None
        result.append(
            EventOut(
                id=event.id,
                at=event.created_at,
                action=event.action,
                title=labels.timeline.get(event.action, event.action),
                from_status=event.from_status,
                to_status=event.to_status,
                actor=actor_label(event.actor_type, Actor.EMPLOYEE),
                actor_name=actor_name,
                comment=event.comment,
                payload=event.payload,
            )
        )
    return result


def build_card(db: Session, application: Application) -> BackofficeApplicationOut:
    config = get_business_config()
    base = build_application_out(db, application, Actor.EMPLOYEE)
    scoring = latest_scoring(db, application.id)
    suggested = default_offer_terms(application, scoring)
    offers = db.scalars(select(Offer).where(Offer.application_id == application.id).order_by(Offer.created_at.desc()))
    info_requests = db.scalars(select(InfoRequest).where(InfoRequest.application_id == application.id).order_by(InfoRequest.created_at.desc()))
    author = application.author
    return BackofficeApplicationOut(
        **base.model_dump(),
        company=build_company(application.company),
        author=AuthorOut(
            full_name=author.full_name,
            login=author.login,
            position_label=config.dictionaries.positions.get(author.position) if author.position else None,
        ),
        checks=build_checks(db, application.id),
        scoring=build_scoring(scoring),
        decision=build_decision(db, application.id),
        suggested_offer=SuggestedOffer(
            amount=suggested.amount,
            term_months=suggested.term_months,
            rate=suggested.rate,
            monthly_payment=suggested.monthly_payment,
            grade_used=grade_for_offer(scoring),
        )
        if suggested
        else None,
        offers=[build_offer(offer) for offer in offers],
        info_requests=[build_info_request(db, item, Actor.EMPLOYEE) for item in info_requests],
        documents=[build_document(document, Actor.EMPLOYEE) for document in list_documents(db, application.id)],
        events=build_events(db, application.id),
    )


# ---------- Решения сотрудника ----------


def check_offer_terms(application: Application, amount: Decimal, term_months: int, rate: Decimal) -> None:
    product = application.product
    if not product.min_amount <= amount <= product.max_amount:
        raise AppError(
            f"Для продукта «{product.name}» доступна сумма от {format_money(product.min_amount)} до {format_money(product.max_amount)} ₽.",
            code="amount_out_of_range",
        )
    if not product.min_term_months <= term_months <= product.max_term_months:
        raise AppError(
            f"Для продукта «{product.name}» доступен срок от {product.min_term_months} до {product.max_term_months} месяцев.",
            code="term_out_of_range",
        )
    if rate < product.base_rate:
        raise AppError(f"Ставка не может быть ниже базовой ставки продукта ({product.base_rate}%).", code="rate_too_low")


def build_employee_offer(db: Session, application: Application, action: str, body: EmployeeActionRequest) -> OfferTerms:
    """Условия предложения сотрудника: то, что он указал, а остальное — по умолчанию (запрошенное и ставка по грейду)."""
    if action == "counter_offer" and (body.amount is None or body.term_months is None):
        raise AppError("Для встречного предложения укажите сумму и срок.", code="offer_terms_required")
    amount = body.amount if body.amount is not None else application.amount
    term = body.term_months if body.term_months is not None else application.term_months
    if amount is None or term is None:
        raise AppError("В заявке нет суммы или срока. Укажите их в решении.", code="offer_terms_required")
    grade = grade_for_offer(latest_scoring(db, application.id))
    rate = body.rate if body.rate is not None else offer_rate(application.product.base_rate, grade, get_business_config().decision)
    check_offer_terms(application, Decimal(amount), term, Decimal(rate))

    same_as_requested = Decimal(amount) == application.amount and term == application.term_months
    offer_type = OFFER_AS_REQUESTED if action == "approve" and same_as_requested else OFFER_COUNTER
    return OfferTerms(offer_type, Decimal(amount), term, Decimal(rate), annuity_payment(amount, rate, term))


def check_info_request(body: EmployeeActionRequest) -> None:
    config = get_business_config()
    unknown_fields = [field for field in body.requested_fields if field not in config.labels.fields]
    if unknown_fields:
        raise AppError(f"Неизвестные поля анкеты: {', '.join(unknown_fields)}.", code="unknown_fields")
    for kind in body.requested_documents:
        kind_config = config.dictionaries.document_kind(kind)
        if kind_config is None or not kind_config.client_can_upload:
            raise AppError(f"Неизвестный вид документа: {kind}.", code="unknown_document_kind")


def perform_employee_action(db: Session, user: User, application_id: uuid.UUID, action: str, body: EmployeeActionRequest) -> Application:
    if action not in EMPLOYEE_ACTIONS:
        raise NotFoundError(f"Неизвестное действие «{action}». Доступные действия: {', '.join(EMPLOYEE_ACTIONS)}.", code="unknown_action")
    get_application(db, application_id)

    try:
        application = lock_application(db, application_id)
        check_version(application, body.version)
        # Сначала проверяем, что действие вообще допустимо (понятный 409), и только потом — сумму и срок
        ensure_transition_allowed(db, application, action, Actor.EMPLOYEE, body.comment)

        payload: dict = {"employee_id": str(user.id)}
        offer_terms = None
        if action in ("approve", "counter_offer"):
            offer_terms = build_employee_offer(db, application, action, body)
            payload["offer"] = {
                "offer_type": offer_terms.offer_type,
                "amount": float(offer_terms.amount),
                "term_months": offer_terms.term_months,
                "rate": float(offer_terms.rate),
            }
        if action == "request_info":
            check_info_request(body)
            payload["requested_fields"] = body.requested_fields
            payload["requested_documents"] = body.requested_documents

        application, _ = apply_transition(db, application_id, action, Actor.EMPLOYEE, user_id=user.id, comment=body.comment, payload=payload)
        if offer_terms:
            create_offer(db, application, offer_terms, created_by_user_id=user.id)
        if action == "request_info":
            create_info_request(
                db,
                application,
                comment=body.comment,
                fields=[{"field": field} for field in body.requested_fields],
                documents=body.requested_documents,
                created_by_type=Actor.EMPLOYEE.value,
                created_by_user_id=user.id,
            )
        db.commit()
    except ConflictError as error:
        db.rollback()
        if error.code == "transition_not_allowed" and is_repeat_of_last_action(db, application_id, action, user.id):
            return db.get(Application, application_id, populate_existing=True)
        raise
    except AppError:
        db.rollback()
        raise
    logger.info("Решение сотрудника", extra={"application_id": str(application_id), "action": action, "user_id": str(user.id)})
    return application
