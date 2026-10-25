"""Юнит-тесты: аннуитетный платёж и проверка ИНН."""

from decimal import Decimal

import pytest

from app.domain.inn import is_valid_inn
from app.domain.formatting import days_text, months_genitive, months_text
from app.domain.payments import ANNUITY, DIFFERENTIATED, annuity_payment, max_amount_for_payment, payment_schedule, payment_summary, schedule_summary


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


# ---------- график платежей и два вида платежа ----------


def test_differentiated_schedule_decreases_and_repays_everything():
    rows = payment_schedule(Decimal(1_200_000), Decimal("17.5"), 12, DIFFERENTIATED)
    assert len(rows) == 12
    assert rows[0]["payment"] == Decimal("117500.00")  # 100 000 долга + 17 500 процентов
    assert rows[-1]["balance"] == Decimal("0.00")
    payments = [row["payment"] for row in rows]
    assert payments == sorted(payments, reverse=True)
    assert sum(row["principal"] for row in rows) == Decimal("1200000.00")
    assert all(row["payment"] == row["principal"] + row["interest"] for row in rows)


def test_annuity_schedule_has_equal_payments_and_matches_summary():
    rows = payment_schedule(Decimal(1_500_000), Decimal("17.5"), 24, ANNUITY)
    assert {row["payment"] for row in rows} == {Decimal("74524.27")}
    assert rows[-1]["balance"] == Decimal("0.00")
    assert sum(row["principal"] for row in rows) == Decimal("1500000.00")
    # Итог по графику совпадает с итогом, который показывают в предложении банка
    summary = payment_summary(Decimal(1_500_000), Decimal("17.5"), 24)
    assert schedule_summary(rows, Decimal(1_500_000))["total_payment"] == summary["total_payment"]


def test_differentiated_overpayment_is_lower_than_annuity():
    annuity = schedule_summary(payment_schedule(Decimal(1_000_000), Decimal(20), 36, ANNUITY), Decimal(1_000_000))
    differentiated = schedule_summary(payment_schedule(Decimal(1_000_000), Decimal(20), 36, DIFFERENTIATED), Decimal(1_000_000))
    assert differentiated["overpayment"] < annuity["overpayment"]
    assert differentiated["first_payment"] > annuity["first_payment"] > differentiated["last_payment"]


@pytest.mark.parametrize(
    ("number", "days", "months", "months_after_up_to"),
    [
        (1, "1 день", "1 месяц", "1 месяца"),
        (3, "3 дня", "3 месяца", "3 месяцев"),
        (5, "5 дней", "5 месяцев", "5 месяцев"),
        (11, "11 дней", "11 месяцев", "11 месяцев"),
        (21, "21 день", "21 месяц", "21 месяца"),
        (24, "24 дня", "24 месяца", "24 месяцев"),
        (65, "65 дней", "65 месяцев", "65 месяцев"),
    ],
)
def test_plural_forms(number, days, months, months_after_up_to):
    assert days_text(number) == days
    assert months_text(number) == months
    assert months_genitive(number) == months_after_up_to
