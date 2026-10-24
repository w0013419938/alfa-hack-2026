"""Кредитное решение по правилам config/decision.yaml (отдельно от скоринга).

Порядок:
  1. Стоп-факторы → отказ.
  2. Уточнения запрашивал сотрудник → снова к сотруднику.
  3. Внешний сервис не ответил → ручное рассмотрение.
  4. Не хватает данных → запрос уточнений.
  5. Решение по грейду: одобрить / встречное предложение / ручное рассмотрение / отказ.
  6. Если нагрузка выше допустимой — встречное предложение с меньшей суммой или большим сроком.
Ставка = базовая ставка продукта + надбавка по грейду; платёж — аннуитетный.
Функции чистые (без БД) — их легко проверить юнит-тестами.
"""

from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal

from app.core.business_config import DecisionFile
from app.domain.formatting import format_money, format_percent
from app.domain.payments import annuity_payment, max_amount_for_payment
from app.domain.scoring import ScoringFacts
from app.models.offer import OFFER_AS_REQUESTED, OFFER_COUNTER

APPROVE = "approve"
COUNTER_OFFER = "counter_offer"
MANUAL_REVIEW = "manual_review"
REJECT = "reject"
NEEDS_INFO = "needs_info"


@dataclass
class OfferTerms:
    offer_type: str  # as_requested / counter_offer
    amount: Decimal
    term_months: int
    rate: Decimal
    monthly_payment: Decimal


@dataclass
class DecisionReason:
    code: str
    text: str


@dataclass
class Decision:
    outcome: str  # approve / counter_offer / manual_review / reject / needs_info
    reasons: list[DecisionReason] = field(default_factory=list)
    offer: OfferTerms | None = None
    requested_documents: list[str] = field(default_factory=list)
    info_comment: str | None = None

    def reasons_text(self) -> str:
        return "; ".join(reason.text for reason in self.reasons)


@dataclass
class DecisionInput:
    amount: Decimal
    term_months: int
    monthly_revenue: Decimal
    product_base_rate: Decimal
    product_min_amount: Decimal
    product_max_amount: Decimal
    product_max_term_months: int
    grade: str
    facts: ScoringFacts
    failed_checks: list[str]  # названия сервисов, которые не ответили
    company_has_reported_revenue: bool
    uploaded_document_kinds: set[str]
    # Сотрудник уже запрашивал уточнения по этой заявке — значит, окончательное решение за ним
    employee_requested_info: bool = False


def offer_rate(base_rate: Decimal, grade: str, config: DecisionFile) -> Decimal:
    return (Decimal(base_rate) + config.grade_rules[grade].rate_premium).quantize(Decimal("0.01"))


def round_down(amount: Decimal, step: int) -> Decimal:
    return (Decimal(amount) / step).to_integral_value(rounding=ROUND_DOWN) * step


def find_counter_offer(data: DecisionInput, rate: Decimal, amount_share: Decimal, config: DecisionFile) -> OfferTerms | None:
    """Подбирает сумму и срок, при которых долговая нагрузка не выше допустимой.

    Сначала пробуем сохранить сумму (запрошенная × amount_share), увеличивая срок с шагом term_step_months.
    Если не получается даже на максимальном сроке — уменьшаем сумму до максимально доступной.
    """
    settings = config.counter_offer
    target = round_down(data.amount * amount_share, settings.amount_round_to)
    target = min(max(target, data.product_min_amount), data.amount)

    max_payment = Decimal(config.max_debt_to_income) * data.monthly_revenue - data.facts.current_loan_payments
    if max_payment <= 0:
        return None

    terms = list(range(data.term_months, data.product_max_term_months + 1, settings.term_step_months))
    if data.product_max_term_months not in terms:
        terms.append(data.product_max_term_months)

    for term in terms:
        if max_amount_for_payment(max_payment, rate, term) >= target:
            return OfferTerms(OFFER_COUNTER, target, term, rate, annuity_payment(target, rate, term))

    best_term = terms[-1]
    best_amount = round_down(max_amount_for_payment(max_payment, rate, best_term), settings.amount_round_to)
    best_amount = min(best_amount, data.product_max_amount)
    if best_amount < data.product_min_amount:
        return None
    return OfferTerms(OFFER_COUNTER, best_amount, best_term, rate, annuity_payment(best_amount, rate, best_term))


def make_decision(data: DecisionInput, config: DecisionFile, reason_texts: dict[str, str], company_status_labels: dict[str, str]) -> Decision:
    facts = data.facts
    stop = config.stop_factors

    def reason(code: str, **values) -> DecisionReason:
        return DecisionReason(code=code, text=reason_texts[code].format(**values))

    # 1. Стоп-факторы (по тем данным, что удалось получить)
    stop_reasons = []
    if facts.company_not_found:
        stop_reasons.append(reason("company_not_found"))
    if facts.company_status in stop.forbidden_company_statuses:
        stop_reasons.append(reason("company_inactive", company_status=company_status_labels.get(facts.company_status, facts.company_status)))
    if facts.current_overdue_days is not None and facts.current_overdue_days > stop.max_current_overdue_days:
        stop_reasons.append(reason("current_overdue", days=facts.current_overdue_days))
    age = facts.values.business_age_months
    if age is not None and age < stop.min_business_age_months:
        stop_reasons.append(reason("business_too_young", months=stop.min_business_age_months))
    if stop_reasons:
        return Decision(outcome=REJECT, reasons=stop_reasons)

    # 2. Заявка уже была у специалиста и он запросил уточнения — после ответа клиента решает снова он,
    #    иначе клиент мог бы «поправить» анкету и обойти ручное рассмотрение
    if data.employee_requested_info:
        return Decision(outcome=MANUAL_REVIEW, reasons=[reason("returned_to_employee")])

    # 3. Внешний сервис не ответил — без полной картины решение принимает человек
    if data.failed_checks:
        return Decision(outcome=config.integration_error_decision, reasons=[reason("integration_error", sources=", ".join(data.failed_checks))])

    # 4. Не хватает данных
    revenue_rule = config.needs_info.missing_company_revenue
    if revenue_rule.enabled and not data.company_has_reported_revenue and revenue_rule.document_kind not in data.uploaded_document_kinds:
        return Decision(
            outcome=NEEDS_INFO,
            reasons=[DecisionReason(code="missing_company_revenue", text=revenue_rule.comment)],
            requested_documents=[revenue_rule.document_kind],
            info_comment=revenue_rule.comment,
        )

    # 5. Решение по грейду
    rule = config.grade_rules[data.grade]
    if rule.decision == REJECT:
        return Decision(outcome=REJECT, reasons=[reason("low_grade")])
    if rule.decision == MANUAL_REVIEW:
        return Decision(outcome=MANUAL_REVIEW, reasons=[reason("border_grade")])

    rate = offer_rate(data.product_base_rate, data.grade, config)
    # Нагрузку проверяем по фактической ставке предложения (с надбавкой за грейд),
    # а не по базовой, как в скоринге: иначе можно одобрить кредит с нагрузкой выше допустимой
    payment = annuity_payment(data.amount, rate, data.term_months)
    dti = (data.facts.current_loan_payments + payment) / data.monthly_revenue
    too_much_debt = dti > config.max_debt_to_income

    reasons = []
    amount_share = Decimal(1)
    if rule.decision == COUNTER_OFFER:
        amount_share = rule.amount_share
        reasons.append(reason("grade_counter_offer", share=format_percent(rule.amount_share * 100)))
    if too_much_debt:
        reasons.append(
            reason(
                "high_debt_load",
                dti=round(dti * 100),
                max_dti=format_percent(config.max_debt_to_income * 100),
                current_payments=format_money(data.facts.current_loan_payments),
            )
        )

    if not reasons:
        return Decision(
            outcome=APPROVE,
            reasons=[reason("approved")],
            offer=OfferTerms(OFFER_AS_REQUESTED, Decimal(data.amount), data.term_months, rate, payment),
        )

    # 6. Встречное предложение
    offer = find_counter_offer(data, rate, amount_share, config)
    if offer is None:
        return Decision(outcome=config.counter_offer.if_impossible, reasons=[*reasons, reason("counter_offer_impossible")])
    return Decision(outcome=COUNTER_OFFER, reasons=reasons, offer=offer)
