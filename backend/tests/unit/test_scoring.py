"""Юнит-тесты скоринга: каждый фактор, отсутствие данных, грейды, сбор фактов.

Диапазоны и баллы берутся из config/scoring.yaml, поэтому тесты проверяют логику,
а не конкретные значения-заглушки (их ещё поменяет участник 2).
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.business_config import get_business_config
from app.domain.scoring import FactorValues, calculate_score, collect_facts, industry_risk_group, months_between, score_factor

CONFIG = get_business_config().scoring
FACTORS = {factor.code: factor for factor in CONFIG.factors}


def value_inside(rule) -> float:
    """Значение, которое точно попадает в диапазон [min, max)."""
    if rule.min is None:
        return rule.max - 0.01 if isinstance(rule.max, float) and rule.max < 2 else rule.max - 1
    return rule.min


@pytest.mark.parametrize("factor_code", [factor.code for factor in CONFIG.factors if factor.bins])
def test_every_bin_of_every_numeric_factor(factor_code):
    factor = FACTORS[factor_code]
    for rule in factor.bins:
        points, explanation = score_factor(factor, value_inside(rule))
        assert points == rule.points, f"{factor_code}: значение {value_inside(rule)} должно дать {rule.points}"
        assert explanation == rule.explanation


@pytest.mark.parametrize("factor_code", [factor.code for factor in CONFIG.factors if factor.categories])
def test_every_category_of_categorical_factor(factor_code):
    factor = FACTORS[factor_code]
    for category in factor.categories:
        assert score_factor(factor, category.value) == (category.points, category.explanation)


@pytest.mark.parametrize("factor_code", [factor.code for factor in CONFIG.factors])
def test_missing_value_gives_missing_points(factor_code):
    factor = FACTORS[factor_code]
    assert score_factor(factor, None) == (factor.missing_points, factor.missing_explanation)


def test_bin_boundaries_min_inclusive_max_exclusive():
    factor = FACTORS["debt_load"]
    first, second = factor.bins[0], factor.bins[1]
    assert score_factor(factor, first.max)[0] == second.points  # граница относится к следующему диапазону


def test_best_values_give_max_score_and_best_grade():
    best = FactorValues(
        business_age_months=600,
        debt_to_income=0.0,
        max_overdue_days=0,
        bki_rating=850,
        amount_to_annual_revenue=0.01,
        industry_risk_group="low",
    )
    result = calculate_score(best, CONFIG)
    assert result.total_score == result.max_score
    assert result.grade == max(CONFIG.grades, key=lambda grade: grade.min_score).grade
    assert len(result.factors) == len(CONFIG.factors)


def test_no_data_gives_worst_grade():
    result = calculate_score(FactorValues(), CONFIG)
    assert result.total_score == sum(factor.missing_points for factor in CONFIG.factors)
    assert result.grade == min(CONFIG.grades, key=lambda grade: grade.min_score).grade


@pytest.mark.parametrize("grade", CONFIG.grades, ids=lambda grade: grade.grade)
def test_grade_threshold(grade):
    """Балл ровно на пороге грейда даёт этот грейд."""
    ordered = sorted(CONFIG.grades, key=lambda item: item.min_score, reverse=True)
    picked = next(item for item in ordered if grade.min_score >= item.min_score)
    assert picked.grade == grade.grade


def test_factor_explanations_present():
    result = calculate_score(FactorValues(business_age_months=40, debt_to_income=0.4), CONFIG)
    for factor in result.factors:
        assert factor.explanation
        assert factor.value_text


def test_months_between():
    assert months_between(date(2020, 1, 15), date(2021, 1, 15)) == 12
    assert months_between(date(2020, 1, 15), date(2021, 1, 14)) == 11
    assert months_between(date(2026, 1, 1), date(2025, 1, 1)) == 0


def test_industry_group_by_okved_prefix():
    risk = CONFIG.industry_risk
    for group, prefixes in risk.groups.items():
        assert industry_risk_group(f"{prefixes[0]}.11", risk) == group
    assert industry_risk_group("99.99", risk) == risk.default
    assert industry_risk_group(None, risk) == risk.default


def make_application(**overrides):
    data = {"amount": Decimal(1_000_000), "term_months": 12, "monthly_revenue": Decimal(500_000), "current_loan_payments": Decimal(20_000)}
    data.update(overrides)
    return SimpleNamespace(**data)


COMPANY = SimpleNamespace(registration_date=date(2020, 1, 1), okved="47.11")


def test_collect_facts_uses_larger_of_declared_and_bki_payments():
    bki = {"rating": 700, "active_loans": [{"monthly_payment": 50_000, "current_overdue_days": 0}], "overdue_history": {"max_days": 5}}
    facts = collect_facts(make_application(), COMPANY, Decimal(12), None, bki, CONFIG.industry_risk, date(2026, 1, 1))
    assert facts.current_loan_payments == Decimal(50_000)
    expected_dti = float((Decimal(50_000) + facts.new_payment) / Decimal(500_000))
    assert facts.values.debt_to_income == pytest.approx(expected_dti, abs=0.0001)
    assert facts.values.max_overdue_days == 5
    assert facts.values.bki_rating == 700


def test_collect_facts_without_bki_uses_declared_payments_and_leaves_bki_factors_empty():
    facts = collect_facts(make_application(), COMPANY, Decimal(12), None, None, CONFIG.industry_risk, date(2026, 1, 1))
    assert facts.current_loan_payments == Decimal(20_000)
    assert facts.values.bki_rating is None
    assert facts.values.max_overdue_days is None
    assert facts.current_overdue_days is None


def test_collect_facts_prefers_registry_registration_date_and_okved():
    egrul = {"registration_date": "2025-07-01", "okved": "62.01", "status": "active"}
    facts = collect_facts(make_application(), COMPANY, Decimal(12), egrul, None, CONFIG.industry_risk, date(2026, 1, 1))
    assert facts.values.business_age_months == 6
    assert facts.values.industry_risk_group == industry_risk_group("62.01", CONFIG.industry_risk)
    assert facts.company_status == "active"


def test_collect_facts_current_overdue_and_amount_to_revenue():
    bki = {"active_loans": [{"monthly_payment": 1, "current_overdue_days": 40}, {"monthly_payment": 1, "current_overdue_days": 10}]}
    facts = collect_facts(make_application(), COMPANY, Decimal(12), None, bki, CONFIG.industry_risk, date(2026, 1, 1))
    assert facts.current_overdue_days == 40
    assert facts.values.max_overdue_days == 40
    assert facts.values.amount_to_annual_revenue == pytest.approx(1_000_000 / (500_000 * 12), abs=0.0001)
