"""Форматирование чисел для текстов, которые читает человек."""

from decimal import Decimal


def format_money(value: Decimal | int | float) -> str:
    """1500000 → «1 500 000», 1234.5 → «1 234,50»."""
    value = Decimal(value)
    if value == value.to_integral_value():
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def plural(number: int, one: str, few: str, many: str) -> str:
    """Форма слова по числу: 1 день, 3 дня, 5 дней, 21 день."""
    number = abs(int(number))
    if number % 100 in range(11, 15):
        return many
    if number % 10 == 1:
        return one
    if number % 10 in (2, 3, 4):
        return few
    return many


def days_text(number: int) -> str:
    return f"{number} {plural(number, 'день', 'дня', 'дней')}"


def months_text(number: int) -> str:
    return f"{number} {plural(number, 'месяц', 'месяца', 'месяцев')}"


def years_text(number: int) -> str:
    return f"{number} {plural(number, 'год', 'года', 'лет')}"


def months_genitive(number: int) -> str:
    """После «до», «меньше»: до 24 месяцев, меньше 3 месяцев, до 21 месяца."""
    return f"{number} {plural(number, 'месяца', 'месяцев', 'месяцев')}"


def format_percent(value: Decimal | float) -> str:
    """17.50 → «17,5», 0.456 → «0,456»."""
    text = f"{Decimal(str(value)).normalize():f}"
    return text.replace(".", ",")
