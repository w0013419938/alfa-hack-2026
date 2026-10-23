"""Форматирование чисел для текстов, которые читает человек."""

from decimal import Decimal


def format_money(value: Decimal | int | float) -> str:
    """1500000 → «1 500 000», 1234.5 → «1 234,50»."""
    value = Decimal(value)
    if value == value.to_integral_value():
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def format_percent(value: Decimal | float) -> str:
    """17.50 → «17,5», 0.456 → «0,456»."""
    text = f"{Decimal(str(value)).normalize():f}"
    return text.replace(".", ",")
