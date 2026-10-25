"""Юнит-тесты кредитного решения. Пороги берутся из config/decision.yaml."""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.core.business_config import get_business_config
from app.domain import decision as d
from app.domain.formatting import months_genitive
from app.domain.payments import annuity_payment
from app.domain.scoring import FactorValues, ScoringFacts

CONFIG = get_business_config()
RULES = CONFIG.decision
LABELS = CONFIG.labels
GRADES_BY_DECISION = {}
for grade_code, rule in RULES.grade_rules.items():
    GRADES_BY_DECISION.setdefault(rule.decision, grade_code)


def grade_for(decision_kind: str) -> str:
    if decision_kind not in GRADES_BY_DECISION:
        pytest.skip(f"В decision.yaml нет грейда с решением {decision_kind}")
    return GRADES_BY_DECISION[decision_kind]


def make_input(**overrides) -> d.DecisionInput:
    facts = ScoringFacts(
        values=FactorValues(business_age_months=60, debt_to_income=0.2),
        current_loan_payments=Decimal(0),
        new_payment=Decimal(50_000),
        current_overdue_days=0,
        company_status="active",
    )
    data = d.DecisionInput(
        amount=Decimal(1_500_000),
        term_months=24,
        monthly_revenue=Decimal(800_000),
        product_base_rate=Decimal("17.5"),
        product_min_amount=Decimal(500_000),
        product_max_amount=Decimal(15_000_000),
        product_max_term_months=36,
        grade=grade_for("approve"),
        facts=facts,
        failed_checks=[],
        company_has_reported_revenue=True,
        uploaded_document_kinds=set(),
    )
    return replace(data, **overrides)


def decide(data: d.DecisionInput) -> d.Decision:
    return d.make_decision(data, RULES, LABELS.decision_reasons, LABELS.company_statuses)


def with_facts(data: d.DecisionInput, **fact_overrides) -> d.DecisionInput:
    return replace(data, facts=replace(data.facts, **fact_overrides))


def test_good_grade_is_approved_as_requested():
    result = decide(make_input())
    assert result.outcome == d.APPROVE
    assert result.offer.offer_type == "as_requested"
    assert result.offer.amount == Decimal(1_500_000)
    assert result.offer.term_months == 24
    grade = make_input().grade
    assert result.offer.rate == Decimal("17.5") + RULES.grade_rules[grade].rate_premium
    assert result.offer.monthly_payment == annuity_payment(Decimal(1_500_000), result.offer.rate, 24)


@pytest.mark.parametrize("status", RULES.stop_factors.forbidden_company_statuses)
def test_liquidated_company_is_rejected(status):
    result = decide(with_facts(make_input(), company_status=status))
    assert result.outcome == d.REJECT
    assert any(reason.code == "company_inactive" for reason in result.reasons)


def test_company_not_found_is_rejected():
    result = decide(with_facts(make_input(), company_not_found=True, company_status=None))
    assert result.outcome == d.REJECT
    assert result.reasons[0].code == "company_not_found"


def test_current_overdue_above_limit_is_rejected_and_at_limit_is_not():
    limit = RULES.stop_factors.max_current_overdue_days
    assert decide(with_facts(make_input(), current_overdue_days=limit + 1)).outcome == d.REJECT
    assert decide(with_facts(make_input(), current_overdue_days=limit)).outcome != d.REJECT


def test_too_young_business_is_rejected():
    young = FactorValues(business_age_months=RULES.stop_factors.min_business_age_months - 1, debt_to_income=0.1)
    result = decide(with_facts(make_input(), values=young))
    assert result.outcome == d.REJECT
    assert result.reasons[0].code == "business_too_young"


def test_all_stop_factors_are_listed():
    data = with_facts(make_input(), company_status=RULES.stop_factors.forbidden_company_statuses[0], current_overdue_days=999)
    codes = {reason.code for reason in decide(data).reasons}
    assert {"company_inactive", "current_overdue"} <= codes


def test_stop_factor_wins_over_integration_error():
    data = with_facts(make_input(failed_checks=["БКИ"]), company_status=RULES.stop_factors.forbidden_company_statuses[0])
    assert decide(data).outcome == d.REJECT


def test_integration_error_goes_to_manual_review():
    result = decide(make_input(failed_checks=["Бюро кредитных историй"]))
    assert result.outcome == RULES.integration_error_decision
    assert result.reasons[0].code == "integration_error"
    assert "Бюро кредитных историй" in result.reasons[0].text


def test_missing_company_revenue_requests_document():
    rule = RULES.needs_info.missing_company_revenue
    if not rule.enabled:
        pytest.skip("Правило выключено в decision.yaml")
    result = decide(make_input(company_has_reported_revenue=False))
    assert result.outcome == d.NEEDS_INFO
    assert result.requested_documents == [rule.document_kind]
    assert result.info_comment


def test_missing_company_revenue_with_document_is_not_blocking():
    rule = RULES.needs_info.missing_company_revenue
    result = decide(make_input(company_has_reported_revenue=False, uploaded_document_kinds={rule.document_kind}))
    assert result.outcome == d.APPROVE


def test_manual_review_grade():
    result = decide(make_input(grade=grade_for("manual_review")))
    assert result.outcome == d.MANUAL_REVIEW
    assert result.reasons[0].code == "border_grade"


def test_reject_grade():
    result = decide(make_input(grade=grade_for("reject")))
    assert result.outcome == d.REJECT
    assert result.reasons[0].code == "low_grade"


def test_counter_offer_grade_reduces_amount_by_share():
    grade = grade_for("counter_offer")
    share = RULES.grade_rules[grade].amount_share
    result = decide(make_input(grade=grade))
    assert result.outcome == d.COUNTER_OFFER
    assert result.offer.offer_type == "counter_offer"
    assert result.offer.amount <= Decimal(1_500_000) * share
    assert result.offer.amount % RULES.counter_offer.amount_round_to == 0
    assert result.offer.rate == Decimal("17.5") + RULES.grade_rules[grade].rate_premium


def debt_load_after(data: d.DecisionInput) -> Decimal:
    """Нагрузка, если выдать запрошенное по ставке грейда."""
    rate = d.offer_rate(data.product_base_rate, data.grade, RULES)
    return (data.facts.current_loan_payments + annuity_payment(data.amount, rate, data.term_months)) / data.monthly_revenue


def test_high_debt_load_gives_counter_offer_within_allowed_load():
    current_payments = Decimal(380_000)
    data = with_facts(make_input(), current_loan_payments=current_payments)
    assert debt_load_after(data) > RULES.max_debt_to_income
    result = decide(data)
    assert result.outcome == d.COUNTER_OFFER
    assert any(reason.code == "high_debt_load" for reason in result.reasons)
    new_load = (current_payments + result.offer.monthly_payment) / Decimal(800_000)
    assert new_load <= RULES.max_debt_to_income


def test_debt_load_is_checked_with_offer_rate_not_base_rate():
    """Нагрузка в норме по базовой ставке, но выше нормы по ставке с надбавкой грейда → не «как запрошено»."""
    grade = next((code for code, rule in RULES.grade_rules.items() if rule.decision == "approve" and rule.rate_premium > 0), None)
    if grade is None:
        pytest.skip("Нет одобряемого грейда с надбавкой к ставке")
    base_payment = annuity_payment(Decimal(1_500_000), Decimal("17.5"), 24)
    # Подбираем текущие платежи так, чтобы по базовой ставке нагрузка была ровно на пределе
    current = RULES.max_debt_to_income * Decimal(800_000) - base_payment
    data = with_facts(make_input(grade=grade), current_loan_payments=current)
    result = decide(data)
    assert result.outcome == d.COUNTER_OFFER
    assert any(reason.code == "high_debt_load" for reason in result.reasons)


def test_counter_offer_prefers_longer_term_over_smaller_amount():
    # Нагрузка чуть выше нормы: ту же сумму можно дать на более долгий срок
    data = with_facts(make_input(), current_loan_payments=Decimal(330_000))
    assert debt_load_after(data) > RULES.max_debt_to_income
    result = decide(data)
    assert result.outcome == d.COUNTER_OFFER
    assert result.offer.amount == Decimal(1_500_000)
    assert result.offer.term_months > 24


def test_counter_offer_impossible_when_no_room_for_payment():
    data = with_facts(make_input(), current_loan_payments=Decimal(800_000))
    result = decide(data)
    assert result.outcome == RULES.counter_offer.if_impossible
    assert any(reason.code == "counter_offer_impossible" for reason in result.reasons)


def test_after_employee_info_request_decision_returns_to_employee():
    result = decide(make_input(employee_requested_info=True))
    assert result.outcome == d.MANUAL_REVIEW
    assert result.reasons[0].code == "returned_to_employee"


def test_stop_factor_still_rejects_after_employee_info_request():
    data = with_facts(make_input(employee_requested_info=True), company_status=RULES.stop_factors.forbidden_company_statuses[0])
    assert decide(data).outcome == d.REJECT


def test_reject_reasons_are_separate_sentences_in_plain_words():
    data = with_facts(make_input(), company_status="liquidating", current_overdue_days=65)
    result = decide(data)
    inline = result.reasons_text(first_lowercase=True)
    assert inline.startswith("по открытым реестрам компания находится в процессе ликвидации. В кредитной истории есть просрочка 65 дней")
    assert inline.endswith("она не погашена.")
    assert "дн." not in inline and "госреестр" not in inline.lower()
    # Для списка причин первая буква заглавная
    assert result.reasons_text().startswith("По открытым реестрам")


def test_young_business_reason_uses_months_in_genitive():
    young = FactorValues(business_age_months=RULES.stop_factors.min_business_age_months - 1, debt_to_income=0.1)
    texts = [reason.text for reason in decide(with_facts(make_input(), values=young)).reasons]
    assert any(f"меньше {months_genitive(RULES.stop_factors.min_business_age_months)}" in text for text in texts)
