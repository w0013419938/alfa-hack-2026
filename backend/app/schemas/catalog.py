"""Схемы справочников: продукты, цели, калькулятор, подбор продукта."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.application import ProductShort
from app.schemas.common import Money


class CodeLabel(BaseModel):
    code: str
    label: str


class PurposeOut(CodeLabel):
    requires_comment: bool


class DocumentKindOut(CodeLabel):
    client_can_upload: bool


class FieldOut(BaseModel):
    field: str
    label: str


class ProductOut(BaseModel):
    code: str
    name: str
    description: str
    suitable_for: str
    purposes: list[CodeLabel]
    min_amount: Money
    max_amount: Money
    min_term_months: int
    max_term_months: int
    base_rate: Money
    rate_text: str  # «от 17,5% годовых»
    requires_collateral: bool
    decision_days: int
    required_fields: list[FieldOut]


class RecommendRequest(BaseModel):
    purpose_code: str = Field(examples=["working_capital"])
    amount: Decimal = Field(gt=0, le=1_000_000_000, examples=[1500000])
    term_months: int = Field(gt=0, le=360, examples=[24])
    urgency: Literal["asap", "week", "month"] = Field(
        default="week", description="Как быстро нужны деньги: asap значит срочно, week в течение недели, month в течение месяца"
    )
    has_collateral: bool = Field(default=False, description="Есть ли залог (недвижимость, транспорт, оборудование)")


class RecommendationOut(BaseModel):
    product: ProductOut
    score: int
    max_score: int
    suitable: bool
    reasons: list[str]
    warnings: list[str]


class CalculatorOut(BaseModel):
    product: ProductShort
    amount: Money
    term_months: int
    rate: Money
    monthly_payment: Money
    total_payment: Money
    overpayment: Money
    note: str
