"""Юнит-тесты: аннуитетный платёж и проверка ИНН."""

from decimal import Decimal

import pytest

from app.domain.inn import is_valid_inn
from app.domain.payments import annuity_payment, max_amount_for_payment, payment_summary


def reference_annuity(amount: float, annual_rate: float, months: int) -> float:
    """Независимый расчёт той же формулы во float — для сверки."""
    rate = annual_rate / 12 / 100
    return amount * rate / (1 - (1 + rate) ** -months)


@pytest.mark.parametrize(
    ("amount", "rate", "months"),
    [(1_500_000, 17.5, 24), (100_000, 21.9, 3), (30_000_000, 16.0, 60), (500_000, 12.0, 12)],
)
def test_annuity_matches_reference(amount, rate, months):
    payment = annuity_payment(Decimal(amount), Decimal(str(rate)), months)
    assert float(payment) == pytest.approx(reference_annuity(amount, rate, months), abs=0.01)


def test_annuity_known_value():
    # 1 200 000 под 12% на 12 мес.: классический пример, платёж 106 618,55
    assert annuity_payment(Decimal(1_200_000), Decimal(12), 12) == Decimal("106618.55")


def test_annuity_zero_rate_is_simple_division():
    assert annuity_payment(Decimal(120_000), Decimal(0), 12) == Decimal("10000.00")


def test_annuity_rejects_zero_term():
    with pytest.raises(ValueError):
        annuity_payment(Decimal(1000), Decimal(10), 0)


def test_max_amount_is_inverse_of_payment():
    payment = annuity_payment(Decimal(2_000_000), Decimal("19.5"), 36)
    amount = max_amount_for_payment(payment, Decimal("19.5"), 36)
    assert abs(amount - Decimal(2_000_000)) < Decimal(100)


def test_payment_summary_totals():
    summary = payment_summary(Decimal(1_200_000), Decimal(12), 12)
    assert summary["total_payment"] == summary["monthly_payment"] * 12
    assert summary["overpayment"] == summary["total_payment"] - Decimal(1_200_000)


@pytest.mark.parametrize("inn", ["7701001012", "7710005052", "770100010180", "770200020287"])
def test_valid_inn(inn):
    assert is_valid_inn(inn)


@pytest.mark.parametrize(
    "inn",
    [
        "7701001013",  # неверная контрольная цифра
        "770100010181",  # неверная 12-я цифра
        "770100010170",  # неверная 11-я цифра
        "12345",  # неверная длина
        "77010010121",  # 11 цифр
        "77010010A2",  # не цифры
        "",
        None,
    ],
)
def test_invalid_inn(inn):
    assert not is_valid_inn(inn)
