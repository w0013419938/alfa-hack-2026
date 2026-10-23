"""Скоринг: балльная модель по правилам из config/scoring.yaml.

Два шага:
1. collect_factor_values() — собирает значения факторов из анкеты, профиля компании, ЕГРЮЛ и БКИ;
2. calculate_score() — по правилам конфига превращает значения в баллы, грейд и объяснения.
Обе функции чистые (без БД), поэтому каждый фактор легко проверить юнит-тестом.
"""

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal

from app.core.business_config import IndustryRiskConfig, ScoringFactorConfig, ScoringFile
from app.domain.formatting import format_money
from app.domain.payments import annuity_payment

INDUSTRY_GROUP_TEXTS = {"low": "низкий риск", "medium": "средний риск", "high": "повышенный риск"}


@dataclass
class FactorValues:
    """Значения всех источников для факторов. None — данных нет."""

    business_age_months: int | None = None
    debt_to_income: float | None = None
    max_overdue_days: int | None = None
    bki_rating: int | None = None
    amount_to_annual_revenue: float | None = None
    industry_risk_group: str | None = None


@dataclass
class ScoringFacts:
    """Факты о заявке, которые нужны и скорингу, и кредитному решению."""

    values: FactorValues
    current_loan_payments: Decimal  # сколько компания уже платит по кредитам в месяц
    new_payment: Decimal | None  # платёж по новому кредиту по базовой ставке
    current_overdue_days: int | None  # текущая непогашенная просрочка по данным БКИ
    company_status: str | None  # статус в ЕГРЮЛ (active, liquidating ...)
    company_not_found: bool = False


@dataclass
class FactorResult:
    code: str
    name: str
    value: float | int | str | None
    value_text: str
    points: int
    max_points: int
    explanation: str


@dataclass
class ScoreResult:
    total_score: int
    max_score: int
    grade: str
    grade_label: str
    factors: list[FactorResult] = field(default_factory=list)

    def factors_as_dicts(self) -> list[dict]:
        return [asdict(item) for item in self.factors]


def months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(months, 0)


def industry_risk_group(okved: str | None, config: IndustryRiskConfig) -> str:
    if not okved:
        return config.default
    prefix = okved.split(".")[0]
    for group, prefixes in config.groups.items():
        if prefix in prefixes:
            return group
    return config.default


def collect_facts(
    application,
    company,
    product_base_rate: Decimal,
    egrul: dict | None,
    bki: dict | None,
    industry_config: IndustryRiskConfig,
    today: date,
) -> ScoringFacts:
    """application, company — объекты с атрибутами; egrul и bki — ответы сервисов (None, если сервис не ответил)."""
    values = FactorValues()

    # Возраст бизнеса: дата регистрации из госреестра надёжнее, чем из профиля
    registration = company.registration_date
    if egrul and egrul.get("registration_date"):
        registration = date.fromisoformat(egrul["registration_date"])
    if registration:
        values.business_age_months = months_between(registration, today)

    # Текущие платежи: берём большее из анкеты и БКИ (консервативно)
    declared_payments = Decimal(application.current_loan_payments or 0)
    bki_payments = Decimal(0)
    current_overdue_days = None
    if bki is not None:
        loans = bki.get("active_loans") or []
        bki_payments = sum((Decimal(str(loan.get("monthly_payment", 0))) for loan in loans), Decimal(0))
        current_overdue_days = max((int(loan.get("current_overdue_days", 0)) for loan in loans), default=0)
        history_max = int((bki.get("overdue_history") or {}).get("max_days", 0))
        values.max_overdue_days = max(history_max, current_overdue_days)
        if bki.get("rating") is not None:
            values.bki_rating = int(bki["rating"])
    current_payments = max(declared_payments, bki_payments)

    # Долговая нагрузка с учётом нового кредита
    new_payment = None
    revenue = Decimal(application.monthly_revenue or 0)
    if application.amount and application.term_months:
        new_payment = annuity_payment(application.amount, product_base_rate, application.term_months)
        if revenue > 0:
            values.debt_to_income = round(float((current_payments + new_payment) / revenue), 4)
    if application.amount and revenue > 0:
        values.amount_to_annual_revenue = round(float(Decimal(application.amount) / (revenue * 12)), 4)

    okved = (egrul or {}).get("okved") or company.okved
    values.industry_risk_group = industry_risk_group(okved, industry_config)

    return ScoringFacts(
        values=values,
        current_loan_payments=current_payments,
        new_payment=new_payment,
        current_overdue_days=current_overdue_days,
        company_status=(egrul or {}).get("status"),
        company_not_found=bool((egrul or {}).get("not_found")),
    )


def format_value(source: str, value) -> str:
    if value is None:
        return "нет данных"
    if source == "business_age_months":
        years, months = divmod(int(value), 12)
        return f"{years} г. {months} мес." if years else f"{months} мес."
    if source in ("debt_to_income", "amount_to_annual_revenue"):
        return f"{round(value * 100)}%"
    if source == "max_overdue_days":
        return "нет просрочек" if value == 0 else f"{value} дн."
    if source == "industry_risk_group":
        return INDUSTRY_GROUP_TEXTS.get(value, value)
    return format_money(value) if isinstance(value, Decimal) else str(value)


def score_factor(factor: ScoringFactorConfig, value) -> tuple[int, str]:
    if value is None:
        return factor.missing_points, factor.missing_explanation
    if factor.categories:
        for category in factor.categories:
            if category.value == value:
                return category.points, category.explanation
        return factor.missing_points, factor.missing_explanation
    for rule in factor.bins:
        above_min = rule.min is None or value >= rule.min
        below_max = rule.max is None or value < rule.max
        if above_min and below_max:
            return rule.points, rule.explanation
    return factor.missing_points, factor.missing_explanation


def calculate_score(values: FactorValues, config: ScoringFile) -> ScoreResult:
    factors = []
    for factor in config.factors:
        value = getattr(values, factor.source)
        points, explanation = score_factor(factor, value)
        factors.append(
            FactorResult(
                code=factor.code,
                name=factor.name,
                value=value,
                value_text=format_value(factor.source, value),
                points=points,
                max_points=factor.max_points,
                explanation=explanation,
            )
        )
    total = sum(item.points for item in factors)
    max_score = sum(item.max_points for item in factors)

    # Грейды в конфиге — от лучшего к худшему; берём первый, порог которого пройден
    grades = sorted(config.grades, key=lambda item: item.min_score, reverse=True)
    grade = next((item for item in grades if total >= item.min_score), grades[-1])
    return ScoreResult(total_score=total, max_score=max_score, grade=grade.grade, grade_label=grade.label, factors=factors)
