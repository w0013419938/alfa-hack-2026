"""Статусы заявки и роли участников процесса."""

from enum import StrEnum


class ApplicationStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    VALIDATION = "VALIDATION"
    NEEDS_INFO = "NEEDS_INFO"
    CHECKS = "CHECKS"
    SCORING = "SCORING"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    OFFER_SENT = "OFFER_SENT"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    SIGNING = "SIGNING"
    ISSUED = "ISSUED"
    REJECTED = "REJECTED"
    CLIENT_DECLINED = "CLIENT_DECLINED"
    CANCELLED = "CANCELLED"


# Финальные статусы: из них переходов нет
FINAL_STATUSES = {
    ApplicationStatus.ISSUED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.CLIENT_DECLINED,
    ApplicationStatus.CANCELLED,
}

# Статусы, в которых заявку обрабатывает система (пайплайн)
AUTOMATIC_STATUSES = {
    ApplicationStatus.SUBMITTED,
    ApplicationStatus.VALIDATION,
    ApplicationStatus.CHECKS,
    ApplicationStatus.SCORING,
    ApplicationStatus.SIGNING,
}

# Статусы, в которых клиент может редактировать анкету и загружать документы
EDITABLE_STATUSES = {ApplicationStatus.DRAFT, ApplicationStatus.NEEDS_INFO}


class Actor(StrEnum):
    CLIENT = "client"
    EMPLOYEE = "employee"
    SYSTEM = "system"
