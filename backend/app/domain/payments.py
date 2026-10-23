"""Расчёт аннуитетного (равного ежемесячного) платежа.

Формула: платёж = S × r / (1 − (1 + r)^(−n)),
где S — сумма кредита, r — месячная ставка (годовая / 12 / 100), n — срок в месяцах.
"""

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

KOPECK = Decimal("0.01")


def monthly_rate(annual_rate_percent: Decimal) -> Decimal:
    return Decimal(annual_rate_percent) / Decimal(1200)


def annuity_payment(amount: Decimal, annual_rate_percent: Decimal, term_months: int) -> Decimal:
    amount = Decimal(amount)
    if term_months <= 0:
        raise ValueError("Срок должен быть больше нуля")
    if amount <= 0:
        return Decimal("0.00")
    rate = monthly_rate(annual_rate_percent)
    if rate == 0:
        return (amount / term_months).quantize(KOPECK, ROUND_HALF_UP)
    payment = amount * rate / (1 - (1 + rate) ** -term_months)
    return payment.quantize(KOPECK, ROUND_HALF_UP)


def max_amount_for_payment(payment: Decimal, annual_rate_percent: Decimal, term_months: int) -> Decimal:
    """Обратная задача: какую сумму можно взять, если платить не больше payment в месяц."""
    payment = Decimal(payment)
    if payment <= 0 or term_months <= 0:
        return Decimal("0.00")
    rate = monthly_rate(annual_rate_percent)
    if rate == 0:
        return (payment * term_months).quantize(KOPECK, ROUND_DOWN)
    amount = payment * (1 - (1 + rate) ** -term_months) / rate
    return amount.quantize(KOPECK, ROUND_DOWN)


def payment_summary(amount: Decimal, annual_rate_percent: Decimal, term_months: int) -> dict:
    """Платёж, общая сумма выплат и переплата — всё, что нужно показать клиенту."""
    payment = annuity_payment(amount, annual_rate_percent, term_months)
    total = (payment * term_months).quantize(KOPECK)
    return {
        "monthly_payment": payment,
        "total_payment": total,
        "overpayment": (total - Decimal(amount)).quantize(KOPECK),
    }
