"""Загрузка бизнес-конфигов из backend/config/*.yaml.

Структура каждого файла описана Pydantic-моделью: если коллеги ошибутся в конфиге,
бэкенд не запустится и напишет, какое поле неверно. Так ошибка видна сразу, а не на демо.
"""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from app.core.settings import get_settings

# ---------- products.yaml ----------


class ProductConfig(BaseModel):
    code: str
    name: str
    description: str
    suitable_for: str
    purposes: list[str]
    min_amount: Decimal
    max_amount: Decimal
    min_term_months: int
    max_term_months: int
    base_rate: Decimal
    requires_collateral: bool
    decision_days: int
    required_fields: list[str]

    @model_validator(mode="after")
    def check_ranges(self):
        if self.min_amount > self.max_amount:
            raise ValueError(f"{self.code}: min_amount больше max_amount")
        if self.min_term_months > self.max_term_months:
            raise ValueError(f"{self.code}: min_term_months больше max_term_months")
        return self


class RecommendationConfig(BaseModel):
    weights: dict[str, int]
    urgency_days: dict[str, int]
    texts: dict[str, str]


class ProductsFile(BaseModel):
    version: str
    products: list[ProductConfig]
    recommendation: RecommendationConfig


# ---------- dictionaries.yaml ----------


class PurposeConfig(BaseModel):
    code: str
    label: str
    requires_comment: bool = False


class DocumentKindConfig(BaseModel):
    code: str
    label: str
    client_can_upload: bool = True


class DictionariesFile(BaseModel):
    purposes: list[PurposeConfig]
    document_kinds: list[DocumentKindConfig]
    company_types: dict[str, str]
    positions: dict[str, str]

    def purpose(self, code: str | None) -> PurposeConfig | None:
        return next((item for item in self.purposes if item.code == code), None)

    def document_kind(self, code: str | None) -> DocumentKindConfig | None:
        return next((item for item in self.document_kinds if item.code == code), None)


# ---------- scoring.yaml ----------


class ScoringBin(BaseModel):
    min: float | None = None
    max: float | None = None
    points: int
    explanation: str


class ScoringCategory(BaseModel):
    value: str
    points: int
    explanation: str


SCORING_SOURCES = Literal[
    "business_age_months",
    "debt_to_income",
    "max_overdue_days",
    "bki_rating",
    "amount_to_annual_revenue",
    "industry_risk_group",
]


class ScoringFactorConfig(BaseModel):
    code: str
    name: str
    source: SCORING_SOURCES
    missing_points: int = 0
    missing_explanation: str = "Нет данных"
    bins: list[ScoringBin] = Field(default_factory=list)
    categories: list[ScoringCategory] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_rules(self):
        if not self.bins and not self.categories:
            raise ValueError(f"Фактор {self.code}: нужно задать bins или categories")
        return self

    @property
    def max_points(self) -> int:
        points = [item.points for item in self.bins] + [item.points for item in self.categories] + [self.missing_points]
        return max(points)


class GradeConfig(BaseModel):
    grade: str
    min_score: int
    label: str


class IndustryRiskConfig(BaseModel):
    default: str
    groups: dict[str, list[str]]


class ScoringFile(BaseModel):
    version: str
    grades: list[GradeConfig]
    factors: list[ScoringFactorConfig]
    industry_risk: IndustryRiskConfig


# ---------- decision.yaml ----------


class StopFactorsConfig(BaseModel):
    forbidden_company_statuses: list[str]
    max_current_overdue_days: int
    min_business_age_months: int


class GradeRuleConfig(BaseModel):
    decision: Literal["approve", "counter_offer", "manual_review", "reject"]
    rate_premium: Decimal
    amount_share: Decimal = Decimal("1")


class CounterOfferConfig(BaseModel):
    term_step_months: int
    amount_round_to: int
    if_impossible: Literal["manual_review", "reject"]


class MissingRevenueRuleConfig(BaseModel):
    enabled: bool
    document_kind: str
    comment: str


class NeedsInfoConfig(BaseModel):
    missing_company_revenue: MissingRevenueRuleConfig


class ValidationRulesConfig(BaseModel):
    max_expenses_to_revenue: Decimal
    max_loan_payments_to_revenue: Decimal


class DecisionFile(BaseModel):
    version: str
    stop_factors: StopFactorsConfig
    grade_rules: dict[str, GradeRuleConfig]
    max_debt_to_income: Decimal
    counter_offer: CounterOfferConfig
    integration_error_decision: Literal["manual_review", "reject"]
    needs_info: NeedsInfoConfig
    offer_valid_days: int
    manual_review_default_grade: str
    validation: ValidationRulesConfig


# ---------- feed.yaml ----------


class FeedFile(BaseModel):
    max_items: int
    weights: dict[str, int]
    reasons: dict[str, str]


# ---------- labels.yaml ----------


class StatusLabel(BaseModel):
    label: str
    description: str
    employee_description: str


class ActionLabel(BaseModel):
    label: str
    confirm_text: str | None = None


class LabelsFile(BaseModel):
    statuses: dict[str, StatusLabel]
    actions: dict[str, ActionLabel]
    progress_steps: dict[str, str]
    progress_states: dict[str, str]
    timeline: dict[str, str]
    actors: dict[str, str]
    system_comments: dict[str, str]
    decision_reasons: dict[str, str]
    decision_outcomes: dict[str, str]
    company_statuses: dict[str, str]
    offer_types: dict[str, str]
    offer_statuses: dict[str, str]
    check_types: dict[str, str]
    check_statuses: dict[str, str]
    fields: dict[str, str]
    validation: dict[str, str]


# ---------- всё вместе ----------


class BusinessConfig(BaseModel):
    products: ProductsFile
    dictionaries: DictionariesFile
    scoring: ScoringFile
    decision: DecisionFile
    feed: FeedFile
    labels: LabelsFile
    contract_template: str

    @model_validator(mode="after")
    def check_cross_references(self):
        """Проверяем, что файлы согласованы между собой."""
        from app.domain.statuses import ApplicationStatus  # локальный импорт, чтобы избежать цикла

        purpose_codes = {item.code for item in self.dictionaries.purposes}
        for product in self.products.products:
            unknown = set(product.purposes) - purpose_codes
            if unknown:
                raise ValueError(f"products.yaml: у продукта {product.code} неизвестные цели {sorted(unknown)}")
            unknown_fields = set(product.required_fields) - set(self.labels.fields)
            if unknown_fields:
                raise ValueError(f"products.yaml: у продукта {product.code} неизвестные поля {sorted(unknown_fields)}")
        grades = {item.grade for item in self.scoring.grades}
        missing = grades - set(self.decision.grade_rules)
        if missing:
            raise ValueError(f"decision.yaml: нет правил для грейдов {sorted(missing)}")
        if self.decision.manual_review_default_grade not in grades:
            raise ValueError("decision.yaml: manual_review_default_grade должен быть одним из грейдов scoring.yaml")
        from app.domain.progress import STEPS

        missing_steps = set(STEPS) - set(self.labels.progress_steps)
        if missing_steps:
            raise ValueError(f"labels.yaml: нет названий этапов {sorted(missing_steps)} в progress_steps")
        missing_statuses = {status.value for status in ApplicationStatus} - set(self.labels.statuses)
        if missing_statuses:
            raise ValueError(f"labels.yaml: нет текстов для статусов {sorted(missing_statuses)}")
        return self

    def product(self, code: str) -> ProductConfig | None:
        return next((item for item in self.products.products if item.code == code), None)

    def status_label(self, status: str) -> str:
        item = self.labels.statuses.get(status)
        return item.label if item else status


def _read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_business_config(config_dir: Path) -> BusinessConfig:
    return BusinessConfig(
        products=_read_yaml(config_dir / "products.yaml"),
        dictionaries=_read_yaml(config_dir / "dictionaries.yaml"),
        scoring=_read_yaml(config_dir / "scoring.yaml"),
        decision=_read_yaml(config_dir / "decision.yaml"),
        feed=_read_yaml(config_dir / "feed.yaml"),
        labels=_read_yaml(config_dir / "labels.yaml"),
        contract_template=(config_dir / "contract_template.html").read_text(encoding="utf-8"),
    )


@lru_cache
def get_business_config() -> BusinessConfig:
    """Конфиг читается один раз за запуск. Чтобы применить изменения — перезапустите бэкенд."""
    return load_business_config(get_settings().config_dir)
