"""Схемы заявки для клиента.

Каждый ответ с заявкой содержит всё, что нужно фронту для отображения без собственной логики:
status_label, status_description, available_actions, timeline, а также info_request и offer.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import Money

# ---------- Входные данные ----------


class ApplicationCreate(BaseModel):
    product_code: str = Field(examples=["working_capital"])
    amount: Decimal | None = Field(default=None, gt=0, le=1_000_000_000, examples=[1500000])
    term_months: int | None = Field(default=None, gt=0, le=360, examples=[24])
    purpose_code: str | None = Field(default=None, max_length=32, examples=["working_capital"])
    purpose_comment: str | None = Field(default=None, max_length=1000)
    collateral_description: str | None = Field(default=None, max_length=1000)
    monthly_revenue: Decimal | None = Field(default=None, ge=0, le=10_000_000_000, examples=[800000])
    monthly_expenses: Decimal | None = Field(default=None, ge=0, le=10_000_000_000, examples=[550000])
    current_loan_payments: Decimal | None = Field(default=None, ge=0, le=10_000_000_000, examples=[0])


class ApplicationUpdate(BaseModel):
    """Частичное изменение черновика: передайте только те поля, которые меняются."""

    product_code: str | None = None
    amount: Decimal | None = Field(default=None, gt=0, le=1_000_000_000)
    term_months: int | None = Field(default=None, gt=0, le=360)
    purpose_code: str | None = Field(default=None, max_length=32)
    purpose_comment: str | None = Field(default=None, max_length=1000)
    collateral_description: str | None = Field(default=None, max_length=1000)
    monthly_revenue: Decimal | None = Field(default=None, ge=0, le=10_000_000_000)
    monthly_expenses: Decimal | None = Field(default=None, ge=0, le=10_000_000_000)
    current_loan_payments: Decimal | None = Field(default=None, ge=0, le=10_000_000_000)
    version: int | None = Field(default=None, description="Версия заявки из последнего ответа. Если передана и не совпадает — 409.")


class ClientActionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000, description="Необязательный комментарий (например, к уточнениям)")
    version: int | None = Field(default=None, description="Версия заявки из последнего ответа. Если передана и не совпадает — 409.")


# ---------- Ответы ----------


class ActionOut(BaseModel):
    code: str
    label: str
    enabled: bool
    disabled_reason: str | None = None
    requires_comment: bool = False
    confirm_text: str | None = None


class TimelineItem(BaseModel):
    at: datetime
    action: str
    title: str
    status: str
    status_label: str
    actor: str
    comment: str | None = None


class OfferOut(BaseModel):
    id: uuid.UUID
    offer_type: str
    offer_type_label: str
    amount: Money
    term_months: int
    rate: Money
    monthly_payment: Money
    total_payment: Money
    overpayment: Money
    valid_until: datetime
    status: str
    status_label: str
    created_at: datetime


class RequestedField(BaseModel):
    field: str
    label: str
    message: str | None = None


class RequestedDocument(BaseModel):
    kind: str
    label: str
    uploaded: bool


class InfoRequestOut(BaseModel):
    id: uuid.UUID
    comment: str
    fields: list[RequestedField]
    documents: list[RequestedDocument]
    created_by: str
    created_at: datetime
    is_open: bool
    response_comment: str | None = None


class ProductShort(BaseModel):
    code: str
    name: str


class ApplicationOut(BaseModel):
    id: uuid.UUID
    number: int
    status: str
    status_label: str
    status_description: str
    is_final: bool
    product: ProductShort
    amount: Money | None
    term_months: int | None
    purpose_code: str | None
    purpose_label: str | None
    purpose_comment: str | None
    collateral_description: str | None
    monthly_revenue: Money | None
    monthly_expenses: Money | None
    current_loan_payments: Money | None
    version: int
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    available_actions: list[ActionOut]
    timeline: list[TimelineItem]
    info_request: InfoRequestOut | None = Field(description="Что нужно предоставить (есть, когда статус NEEDS_INFO)")
    offer: OfferOut | None = Field(description="Действующее или принятое предложение банка")
    documents_count: int
