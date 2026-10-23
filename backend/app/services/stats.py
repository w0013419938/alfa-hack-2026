"""Простые метрики для бэкофиса."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.business_config import get_business_config
from app.domain.statuses import ApplicationStatus
from app.models import Application, ApplicationEvent
from app.schemas.backoffice import StatsOut, StatusCount

# Первичное решение по заявке: одобрение, встречное предложение, отказ или передача специалисту
FIRST_DECISION_ACTIONS = ["auto_approve", "auto_counter_offer", "auto_reject", "send_to_manual_review", "technical_error"]
AUTO_APPROVE_ACTIONS = ["auto_approve", "auto_counter_offer"]


def format_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} сек."
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} мин. {seconds} сек."
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours} ч. {minutes} мин."
    days, hours = divmod(hours, 24)
    return f"{days} дн. {hours} ч."


def count_applications_with_actions(db: Session, actions: list[str]) -> int:
    return db.scalar(select(func.count(func.distinct(ApplicationEvent.application_id))).where(ApplicationEvent.action.in_(actions))) or 0


def get_stats(db: Session) -> StatsOut:
    labels = get_business_config().labels
    counts = dict(db.execute(select(Application.status, func.count()).group_by(Application.status)).all())
    by_status = [
        StatusCount(status=status.value, label=labels.statuses[status.value].label, count=counts.get(status.value, 0)) for status in ApplicationStatus
    ]

    decided = count_applications_with_actions(db, FIRST_DECISION_ACTIONS)
    auto_approved = count_applications_with_actions(db, AUTO_APPROVE_ACTIONS)
    rate = auto_approved / decided if decided else 0.0

    # Время обработки: от первой отправки до первого решения банка (предложение или отказ)
    average_seconds = db.scalar(
        select(func.avg(func.extract("epoch", Application.decided_at - Application.submitted_at))).where(
            Application.decided_at.is_not(None), Application.submitted_at.is_not(None)
        )
    )
    average_seconds = float(average_seconds) if average_seconds is not None else None

    return StatsOut(
        total=sum(counts.values()),
        by_status=by_status,
        manual_review_queue=counts.get(ApplicationStatus.MANUAL_REVIEW.value, 0),
        decided_count=decided,
        auto_approved_count=auto_approved,
        auto_approval_rate=round(rate, 4),
        auto_approval_rate_text=f"{round(rate * 100)}%",
        average_processing_seconds=round(average_seconds, 1) if average_seconds is not None else None,
        average_processing_text=format_duration(average_seconds) if average_seconds is not None else None,
    )
