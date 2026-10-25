"""Расчёт платежей по кредиту.

Аннуитетный (равный ежемесячный) платёж: платёж = S × r / (1 − (1 + r)^(−n)),
где S — сумма кредита, r — месячная ставка (годовая / 12 / 100), n — срок в месяцах.

Дифференцированный платёж: основной долг делится на равные части, проценты считаются с остатка,
поэтому платёж каждый месяц меньше предыдущего.
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


ANNUITY = "annuity"
DIFFERENTIATED = "differentiated"


def payment_schedule(amount: Decimal, annual_rate_percent: Decimal, term_months: int, payment_type: str = ANNUITY) -> list[dict]:
    """График платежей по месяцам: платёж, основной долг, проценты и остаток долга после платежа."""
    amount = Decimal(amount)
    rate = monthly_rate(annual_rate_percent)
    balance = amount
    rows = []
    if payment_type == DIFFERENTIATED:
        principal_part = (amount / term_months).quantize(KOPECK, ROUND_HALF_UP)
    else:
        fixed_payment = annuity_payment(amount, annual_rate_percent, term_months)
    for month in range(1, term_months + 1):
        interest = (balance * rate).quantize(KOPECK, ROUND_HALF_UP)
        if payment_type == DIFFERENTIATED:
            principal = balance if month == term_months else principal_part
            payment = principal + interest
        else:
            payment = fixed_payment
            # В последнем месяце гасим весь остаток, платёж остаётся прежним
            principal = balance if month == term_months else payment - interest
            interest = payment - principal if month == term_months else interest
        balance = (balance - principal).quantize(KOPECK)
        rows.append({"month": month, "payment": payment, "principal": principal, "interest": interest, "balance": balance})
    return rows


def schedule_summary(rows: list[dict], amount: Decimal) -> dict:
    """Итоги по графику: первый и последний платёж, сколько вернём всего и переплата."""
    total = sum((row["payment"] for row in rows), Decimal("0.00")).quantize(KOPECK)
    return {
        "first_payment": rows[0]["payment"],
        "last_payment": rows[-1]["payment"],
        "total_payment": total,
        "overpayment": (total - Decimal(amount)).quantize(KOPECK),
    }


def payment_summary(amount: Decimal, annual_rate_percent: Decimal, term_months: int) -> dict:
    """Платёж, общая сумма выплат и переплата — всё, что нужно показать клиенту."""
    payment = annuity_payment(amount, annual_rate_percent, term_months)
    total = (payment * term_months).quantize(KOPECK)
    return {
        "monthly_payment": payment,
        "total_payment": total,
        "overpayment": (total - Decimal(amount)).quantize(KOPECK),
    }
