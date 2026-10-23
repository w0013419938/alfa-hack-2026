"""Схемы бэкофиса (рабочее место сотрудника банка)."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.application import ActionOut, ApplicationOut, InfoRequestOut, OfferOut, ProductShort, TimelineItem
from app.schemas.common import Money
from app.schemas.company import CompanyOut, DocumentOut


class EmployeeActionRequest(BaseModel):
    """Тело действия сотрудника. Какие поля нужны — зависит от действия:

    - approve: comment; amount, term_months, rate — по желанию (если не указаны, берутся из suggested_offer);
    - counter_offer: comment, amount, term_months; rate — по желанию;
    - request_info: comment; requested_fields и/или requested_documents — по желанию;
    - reject: comment (причину увидит клиент).
    """

    comment: str = Field(min_length=3, max_length=2000, description="Комментарий обязателен; его увидит клиент в истории заявки")
    amount: Decimal | None = Field(default=None, gt=0, le=1_000_000_000)
    term_months: int | None = Field(default=None, gt=0, le=360)
    rate: Decimal | None = Field(default=None, gt=0, le=100, description="Ставка, % годовых")
    requested_fields: list[str] = Field(default_factory=list, description="Коды полей анкеты, которые нужно исправить")
    requested_documents: list[str] = Field(default_factory=list, description="Коды видов документов, которые нужно загрузить")
    version: int | None = Field(default=None, description="Версия заявки из последнего ответа. Если передана и не совпадает — 409.")


class CheckOut(BaseModel):
    id: uuid.UUID
    check_type: str
    check_type_label: str
    status: str
    status_label: str
    attempts: int
    duration_ms: int
    error_message: str | None
    summary: list[str]  # главное из ответа простыми словами
    response: dict | None  # полный ответ сервиса
    created_at: datetime


class FactorOut(BaseModel):
    code: str
    name: str
    value: float | int | str | None
    value_text: str
    points: int
    max_points: int
    explanation: str


class ScoringOut(BaseModel):
    total_score: int
    max_score: int
    grade: str
    grade_label: str
    debt_to_income: float | None
    rules_version: str
    factors: list[FactorOut]
    created_at: datetime


class DecisionReasonOut(BaseModel):
    code: str
    text: str


class DecisionOut(BaseModel):
    outcome: str
    outcome_label: str
    reasons: list[DecisionReasonOut]
    decided_at: datetime


class SuggestedOffer(BaseModel):
    """Условия по умолчанию для формы «Одобрить»: запрошенные сумма и срок, ставка по грейду."""

    amount: Money
    term_months: int
    rate: Money
    monthly_payment: Money
    grade_used: str


class AuthorOut(BaseModel):
    full_name: str
    login: str
    position_label: str | None


class EventOut(BaseModel):
    id: uuid.UUID
    at: datetime
    action: str
    title: str
    from_status: str | None
    to_status: str
    actor: str
    actor_name: str | None
    comment: str | None
    payload: dict


class BackofficeApplicationOut(ApplicationOut):
    company: CompanyOut
    author: AuthorOut
    checks: list[CheckOut]
    scoring: ScoringOut | None
    decision: DecisionOut | None
    suggested_offer: SuggestedOffer | None
    offers: list[OfferOut]
    info_requests: list[InfoRequestOut]
    documents: list[DocumentOut]
    events: list[EventOut]


class BackofficeListItem(BaseModel):
    id: uuid.UUID
    number: int
    company_name: str
    company_inn: str
    product: ProductShort
    amount: Money | None
    term_months: int | None
    status: str
    status_label: str
    status_description: str
    is_final: bool
    grade: str | None
    score: int | None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    available_actions: list[ActionOut]
    timeline: list[TimelineItem]


class StatusCount(BaseModel):
    status: str
    label: str
    count: int


class StatsOut(BaseModel):
    total: int
    by_status: list[StatusCount]
    manual_review_queue: int
    decided_count: int = Field(description="Заявок, по которым принято первичное решение (автоматически или передано специалисту)")
    auto_approved_count: int = Field(description="Из них одобрено автоматически (на запрошенных или изменённых условиях)")
    auto_approval_rate: float = Field(description="Доля автоодобрений, от 0 до 1")
    auto_approval_rate_text: str
    average_processing_seconds: float | None = Field(description="Среднее время от отправки заявки до решения банка")
    average_processing_text: str | None
