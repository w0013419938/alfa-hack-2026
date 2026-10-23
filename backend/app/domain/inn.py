"""Проверка ИНН по контрольной сумме.

ИНН юрлица — 10 цифр (одна контрольная цифра), ИНН ИП — 12 цифр (две контрольные цифры).
Алгоритм: взвешенная сумма цифр по модулю 11, затем по модулю 10.
"""

WEIGHTS_10 = [2, 4, 10, 3, 5, 9, 4, 6, 8]
WEIGHTS_12_FIRST = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
WEIGHTS_12_SECOND = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]


def _control_digit(digits: list[int], weights: list[int]) -> int:
    return sum(digit * weight for digit, weight in zip(digits, weights, strict=False)) % 11 % 10


def is_valid_inn(inn: str | None) -> bool:
    if not inn or not inn.isdigit() or len(inn) not in (10, 12):
        return False
    digits = [int(char) for char in inn]
    if len(digits) == 10:
        return _control_digit(digits[:9], WEIGHTS_10) == digits[9]
    first_ok = _control_digit(digits[:10], WEIGHTS_12_FIRST) == digits[10]
    second_ok = _control_digit(digits[:11], WEIGHTS_12_SECOND) == digits[11]
    return first_ok and second_ok
