"""Шаг VALIDATION: полнота и корректность анкеты по правилам продукта.

Функция чистая (без БД): на вход — заявка, продукт, ИНН компании и конфиг, на выход — список проблем.
Пустой список — анкета в порядке.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.core.business_config import BusinessConfig
from app.domain.formatting import format_money
from app.domain.inn import is_valid_inn


@dataclass
class ValidationProblem:
    message: str
    field: str | None = None  # поле анкеты, которое нужно исправить (None — проблема не в анкете)


def _is_empty(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def validate_application(application, product, company_inn: str, config: BusinessConfig) -> list[ValidationProblem]:
    """application и product — объекты с атрибутами (модели SQLAlchemy или их аналоги в тестах)."""
    texts = config.labels.validation
    field_labels = config.labels.fields
    rules = config.decision.validation
    problems: list[ValidationProblem] = []

    if not product.is_active:
        problems.append(ValidationProblem(texts["product_inactive"].format(product=product.name), "product_code"))
        return problems

    # 1. Обязательные поля продукта
    for field in product.required_fields:
        if _is_empty(getattr(application, field, None)):
            problems.append(ValidationProblem(texts["required"].format(field=field_labels.get(field, field)), field))

    # 2. Сумма и срок в пределах продукта
    if application.amount is not None and not product.min_amount <= application.amount <= product.max_amount:
        problems.append(
            ValidationProblem(
                texts["amount_range"].format(product=product.name, min=format_money(product.min_amount), max=format_money(product.max_amount)),
                "amount",
            )
        )
    if application.term_months is not None and not product.min_term_months <= application.term_months <= product.max_term_months:
        problems.append(
            ValidationProblem(
                texts["term_range"].format(product=product.name, min=product.min_term_months, max=product.max_term_months),
                "term_months",
            )
        )

    # 3. Цель кредита подходит продукту; для «Другое» нужен комментарий
    if application.purpose_code is not None:
        purpose = config.dictionaries.purpose(application.purpose_code)
        if purpose is None:
            problems.append(ValidationProblem(texts["purpose_unknown"], "purpose_code"))
        elif application.purpose_code not in product.purposes:
            problems.append(ValidationProblem(texts["purpose_not_allowed"].format(purpose=purpose.label, product=product.name), "purpose_code"))
        elif purpose.requires_comment and _is_empty(application.purpose_comment):
            problems.append(ValidationProblem(texts["purpose_comment_required"], "purpose_comment"))

    # 4. ИНН компании корректен (контрольная сумма)
    if not is_valid_inn(company_inn):
        problems.append(ValidationProblem(texts["inn_invalid"]))

    # 5. Цифры разумны
    revenue = application.monthly_revenue
    if revenue is not None and revenue > 0:
        if application.monthly_expenses is not None and application.monthly_expenses > revenue * Decimal(rules.max_expenses_to_revenue):
            problems.append(ValidationProblem(texts["expenses_too_high"], "monthly_expenses"))
        if (
            application.current_loan_payments is not None
            and application.current_loan_payments > revenue * Decimal(rules.max_loan_payments_to_revenue)
        ):
            problems.append(ValidationProblem(texts["payments_too_high"], "current_loan_payments"))
    elif revenue is not None and revenue <= 0 and "monthly_revenue" in product.required_fields:
        problems.append(ValidationProblem(texts["required"].format(field=field_labels["monthly_revenue"]), "monthly_revenue"))

    return problems
