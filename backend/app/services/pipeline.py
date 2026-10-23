"""Пайплайн автоматической обработки заявки.

SUBMITTED → VALIDATION → CHECKS → SCORING → (OFFER_SENT | MANUAL_REVIEW | REJECTED | NEEDS_INFO)
SIGNING → ISSUED

Как устроено:
- каждый шаг смотрит на ТЕКУЩИЙ статус заявки и делает ровно один переход в своей транзакции;
- поэтому обработку можно безопасно запустить заново с любого места (например, после перезапуска бэкенда);
- если статус успели поменять в другом месте (ConflictError), шаг просто останавливается;
- если шаг упал с неожиданной ошибкой, заявка уходит на ручное рассмотрение, а не «зависает».
"""

import logging
import threading
import time
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_config import get_business_config
from app.core.db import SessionLocal
from app.core.errors import ConflictError
from app.core.settings import get_settings
from app.domain import decision as decisions
from app.domain.formatting import format_money, format_percent
from app.domain.scoring import calculate_score, collect_facts
from app.domain.state_machine import apply_transition, find_transition, get_current_offer
from app.domain.statuses import AUTOMATIC_STATUSES, Actor, ApplicationStatus
from app.domain.validation import validate_application
from app.integrations.external_client import ExternalDataClient, get_external_client
from app.models import Application, Document, ExternalCheck, InfoRequest, ScoringResult
from app.models.checks import CHECK_BKI, CHECK_EGRUL, CHECK_OK
from app.services.offers import create_info_request, create_offer

logger = logging.getLogger(__name__)

S = ApplicationStatus
MAX_STEPS = 10  # защита от бесконечного цикла


def capitalize(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def run_pipeline(application_id: uuid.UUID, step_delay: float | None = None, client: ExternalDataClient | None = None) -> None:
    """Проводит заявку по всем автоматическим шагам, пока она не попадёт в статус, где нужен человек."""
    delay = get_settings().pipeline_step_delay_seconds if step_delay is None else step_delay
    client = client or get_external_client()

    for _ in range(MAX_STEPS):
        try:
            with SessionLocal() as db:
                application = db.get(Application, application_id)
                status = application.status if application else None
        except Exception:
            # Например, база кратковременно недоступна. Заявку потом подберёт сторож (resume_unfinished_applications)
            logger.exception("Не удалось прочитать статус заявки", extra={"application_id": str(application_id)})
            return
        if status not in AUTOMATIC_STATUSES:
            return

        if delay:
            time.sleep(delay)  # пауза, чтобы на демо было видно смену статусов
        try:
            run_step(application_id, status, client)
        except ConflictError:
            logger.info("Статус заявки изменился во время шага — останавливаемся", extra={"application_id": str(application_id)})
            return
        except Exception:
            logger.exception("Ошибка на шаге пайплайна", extra={"application_id": str(application_id), "from_status": status})
            send_to_manual_review_after_error(application_id)
            return


def run_step(application_id: uuid.UUID, status: str, client: ExternalDataClient) -> None:
    if status == S.SUBMITTED:
        step_start_validation(application_id)
    elif status == S.VALIDATION:
        step_validation(application_id)
    elif status == S.CHECKS:
        step_checks(application_id, client)
    elif status == S.SCORING:
        step_scoring(application_id)
    elif status == S.SIGNING:
        step_issue(application_id)


def step_start_validation(application_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        apply_transition(db, application_id, "start_validation", Actor.SYSTEM)
        db.commit()


def step_validation(application_id: uuid.UUID) -> None:
    config = get_business_config()
    with SessionLocal() as db:
        application = db.get(Application, application_id)
        problems = validate_application(application, application.product, application.company.inn, config)
        if not problems:
            apply_transition(db, application_id, "validation_passed", Actor.SYSTEM)
            db.commit()
            return

        comment = capitalize(config.labels.system_comments["validation_failed"].format(problems="; ".join(item.message for item in problems)))
        application, _ = apply_transition(
            db,
            application_id,
            "validation_failed",
            Actor.SYSTEM,
            comment=comment,
            payload={"problems": [{"field": item.field, "message": item.message} for item in problems]},
        )
        fields = [{"field": item.field, "message": capitalize(item.message)} for item in problems if item.field]
        create_info_request(db, application, comment=comment, fields=fields)
        db.commit()


def step_checks(application_id: uuid.UUID, client: ExternalDataClient) -> None:
    config = get_business_config()
    with SessionLocal() as db:
        inn = db.get(Application, application_id).company.inn

    # Запросы во внешние сервисы — вне транзакции: они могут идти несколько секунд
    results = [client.get_egrul(inn), client.get_bki_report(inn)]

    with SessionLocal() as db:
        for result in results:
            db.add(
                ExternalCheck(
                    application_id=application_id,
                    check_type=result.check_type,
                    status=result.status,
                    request=result.request,
                    response=result.data,
                    error_message=result.error_message,
                    attempts=result.attempts,
                    duration_ms=result.duration_ms,
                )
            )
        check_names = config.labels.check_types
        ok_names = [check_names[item.check_type] for item in results if item.status == CHECK_OK]
        failed_names = [check_names[item.check_type] for item in results if item.status != CHECK_OK]
        if failed_names:
            comment = config.labels.system_comments["checks_with_errors"].format(sources=", ".join(failed_names))
        else:
            comment = config.labels.system_comments["checks_completed"].format(sources=", ".join(ok_names))
        apply_transition(
            db,
            application_id,
            "checks_completed",
            Actor.SYSTEM,
            comment=comment,
            payload={"checks": {item.check_type: item.status for item in results}},
        )
        db.commit()


def latest_check(db: Session, application_id: uuid.UUID, check_type: str) -> ExternalCheck | None:
    return db.scalar(
        select(ExternalCheck)
        .where(ExternalCheck.application_id == application_id, ExternalCheck.check_type == check_type)
        .order_by(ExternalCheck.created_at.desc())
        .limit(1)
    )


def step_scoring(application_id: uuid.UUID) -> None:
    config = get_business_config()
    labels = config.labels
    with SessionLocal() as db:
        application = db.get(Application, application_id)
        product = application.product
        company = application.company

        egrul_check = latest_check(db, application_id, CHECK_EGRUL)
        bki_check = latest_check(db, application_id, CHECK_BKI)
        egrul = egrul_check.response if egrul_check and egrul_check.status == CHECK_OK else None
        bki = bki_check.response if bki_check and bki_check.status == CHECK_OK else None
        failed_checks = [labels.check_types[check_type] for check_type, data in ((CHECK_EGRUL, egrul), (CHECK_BKI, bki)) if data is None]

        # 1. Скоринг
        facts = collect_facts(application, company, product.base_rate, egrul, bki, config.scoring.industry_risk, date.today())
        score = calculate_score(facts.values, config.scoring)
        db.add(
            ScoringResult(
                application_id=application_id,
                total_score=score.total_score,
                max_score=score.max_score,
                grade=score.grade,
                factors=score.factors_as_dicts(),
                debt_to_income=facts.values.debt_to_income,
                rules_version=config.scoring.version,
            )
        )

        # 2. Кредитное решение
        uploaded_kinds = set(db.scalars(select(Document.kind).where(Document.application_id == application_id)))
        employee_requested_info = (
            db.scalar(
                select(InfoRequest.id)
                .where(InfoRequest.application_id == application_id, InfoRequest.created_by_type == Actor.EMPLOYEE.value)
                .limit(1)
            )
            is not None
        )
        decision = decisions.make_decision(
            decisions.DecisionInput(
                amount=application.amount,
                term_months=application.term_months,
                monthly_revenue=application.monthly_revenue,
                product_base_rate=product.base_rate,
                product_min_amount=product.min_amount,
                product_max_amount=product.max_amount,
                product_max_term_months=product.max_term_months,
                grade=score.grade,
                facts=facts,
                failed_checks=failed_checks,
                company_has_reported_revenue=company.annual_revenue is not None,
                uploaded_document_kinds=uploaded_kinds,
                employee_requested_info=employee_requested_info,
            ),
            config.decision,
            labels.decision_reasons,
            labels.company_statuses,
        )

        # 3. Переход по итогам решения
        payload = {
            "decision": decision.outcome,
            "reasons": [{"code": item.code, "text": item.text} for item in decision.reasons],
            "score": score.total_score,
            "grade": score.grade,
            "debt_to_income": facts.values.debt_to_income,
            "rules_version": {"scoring": config.scoring.version, "decision": config.decision.version},
        }
        apply_decision(db, application, decision, payload)
        db.commit()


def offer_comment(template: str, terms: decisions.OfferTerms, reasons: str = "") -> str:
    return capitalize(
        template.format(
            reasons=reasons,
            amount=format_money(terms.amount),
            term=terms.term_months,
            rate=format_percent(terms.rate),
        )
    )


def apply_decision(db: Session, application: Application, decision: decisions.Decision, payload: dict) -> None:
    comments = get_business_config().labels.system_comments
    reasons = decision.reasons_text()

    if decision.outcome == decisions.APPROVE:
        apply_transition(db, application.id, "auto_approve", Actor.SYSTEM, comment=offer_comment(comments["auto_approve"], decision.offer), payload=payload)
        create_offer(db, application, decision.offer)
    elif decision.outcome == decisions.COUNTER_OFFER:
        comment = offer_comment(comments["auto_counter_offer"], decision.offer, reasons)
        apply_transition(db, application.id, "auto_counter_offer", Actor.SYSTEM, comment=comment, payload=payload)
        create_offer(db, application, decision.offer)
    elif decision.outcome == decisions.REJECT:
        comment = capitalize(comments["auto_reject"].format(reasons=reasons))
        apply_transition(db, application.id, "auto_reject", Actor.SYSTEM, comment=comment, payload=payload)
    elif decision.outcome == decisions.NEEDS_INFO:
        apply_transition(db, application.id, "auto_request_info", Actor.SYSTEM, comment=decision.info_comment, payload=payload)
        create_info_request(db, application, comment=decision.info_comment, documents=decision.requested_documents)
    else:
        comment = capitalize(comments["send_to_manual_review"].format(reasons=reasons))
        apply_transition(db, application.id, "send_to_manual_review", Actor.SYSTEM, comment=comment, payload=payload)


def step_issue(application_id: uuid.UUID) -> None:
    """Имитация выдачи кредита: деньги «перечисляются» на счёт компании."""
    comments = get_business_config().labels.system_comments
    with SessionLocal() as db:
        offer = get_current_offer(db, application_id)
        amount = offer.amount if offer else 0
        apply_transition(
            db,
            application_id,
            "issue",
            Actor.SYSTEM,
            comment=comments["issue"].format(amount=format_money(amount)),
            payload={"amount": float(amount), "issued_at": datetime.now(UTC).isoformat(), "simulated": True},
        )
        db.commit()


def send_to_manual_review_after_error(application_id: uuid.UUID) -> None:
    comments = get_business_config().labels.system_comments
    try:
        with SessionLocal() as db:
            application = db.get(Application, application_id)
            if application and find_transition(application.status, "technical_error"):
                apply_transition(db, application_id, "technical_error", Actor.SYSTEM, comment=comments["technical_error"])
                db.commit()
    except Exception:
        logger.exception("Не удалось передать заявку специалисту после ошибки", extra={"application_id": str(application_id)})


def resume_unfinished_applications(dispatcher, idle_seconds: float = 0) -> int:
    """Возобновляет заявки, которые застряли в автоматических статусах.

    При старте бэкенда (idle_seconds=0) — все такие заявки: их обработка прервалась перезапуском.
    Сторож (start_watchdog) — только те, что не менялись дольше idle_seconds: значит, их шаг упал или потерялся.
    Двойная обработка не страшна: каждый шаг проверяет текущий статус под блокировкой строки.
    """
    threshold = datetime.now(UTC) - timedelta(seconds=idle_seconds)
    with SessionLocal() as db:
        ids = list(
            db.scalars(
                select(Application.id).where(
                    Application.status.in_([status.value for status in AUTOMATIC_STATUSES]),
                    Application.updated_at <= threshold,
                )
            )
        )
    for application_id in ids:
        dispatcher.dispatch(application_id)
    if ids:
        logger.info(f"Возобновлена обработка заявок: {len(ids)}")
    return len(ids)


def start_watchdog(dispatcher) -> threading.Event:
    """Фоновый сторож: раз в PIPELINE_WATCHDOG_INTERVAL_SECONDS ищет застрявшие заявки. Возвращает флаг остановки."""
    settings = get_settings()
    stop = threading.Event()

    def loop() -> None:
        while not stop.wait(settings.pipeline_watchdog_interval_seconds):
            try:
                resume_unfinished_applications(dispatcher, idle_seconds=settings.pipeline_stuck_after_seconds)
            except Exception:
                logger.exception("Сторож пайплайна: ошибка при поиске застрявших заявок")

    threading.Thread(target=loop, name="pipeline-watchdog", daemon=True).start()
    return stop
