"""Подбор кредитного продукта по ответам клиента.

Простая логика на правилах: за каждое совпадение (цель, сумма, срок, скорость, залог) продукт получает
баллы из config/products.yaml (recommendation.weights). Продукты сортируются по баллам.
«Подходит» значит, что у продукта совпали цель, сумма, срок и требования к залогу.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.core.business_config import DictionariesFile, ProductConfig, RecommendationConfig
from app.domain.formatting import days_text, format_money, months_genitive, months_text


@dataclass
class RecommendationInput:
    purpose_code: str
    amount: Decimal
    term_months: int
    urgency: str  # asap / week / month
    has_collateral: bool


@dataclass
class Recommendation:
    product: ProductConfig
    score: int
    max_score: int
    suitable: bool
    reasons: list[str] = field(default_factory=list)  # почему подходит
    warnings: list[str] = field(default_factory=list)  # что не подходит


def recommend_products(
    products: list[ProductConfig],
    dictionaries: DictionariesFile,
    settings: RecommendationConfig,
    request: RecommendationInput,
) -> list[Recommendation]:
    weights = settings.weights
    texts = settings.texts
    purpose = dictionaries.purpose(request.purpose_code)
    purpose_label = purpose.label if purpose else request.purpose_code
    days_client_can_wait = settings.urgency_days.get(request.urgency, max(settings.urgency_days.values()))
    max_score = sum(weights.values())

    results = []
    for product in products:
        item = Recommendation(product=product, score=0, max_score=max_score, suitable=True)

        def check(ok: bool, weight_key: str, ok_text: str, bad_text: str, critical: bool = True) -> None:
            if ok:
                item.score += weights.get(weight_key, 0)
                item.reasons.append(ok_text)
            else:
                item.warnings.append(bad_text)
                if critical:
                    item.suitable = False

        purpose_ok = request.purpose_code in product.purposes
        check(purpose_ok, "purpose", texts["purpose_ok"].format(purpose=purpose_label), texts["purpose_bad"].format(purpose=purpose_label))

        amount_values = {
            "amount": format_money(request.amount),
            "min_amount": format_money(product.min_amount),
            "max_amount": format_money(product.max_amount),
        }
        amount_ok = product.min_amount <= request.amount <= product.max_amount
        check(amount_ok, "amount", texts["amount_ok"].format(**amount_values), texts["amount_bad"].format(**amount_values))

        term_values = {
            "term": request.term_months,
            "term_text": months_text(request.term_months),
            "min_term": product.min_term_months,
            "max_term": product.max_term_months,
            "max_term_text": months_genitive(product.max_term_months),
        }
        term_ok = product.min_term_months <= request.term_months <= product.max_term_months
        check(term_ok, "term", texts["term_ok"].format(**term_values), texts["term_bad"].format(**term_values))

        # Скорость не критична: продукт подходит, просто решение дольше
        speed_ok = product.decision_days <= days_client_can_wait
        check(speed_ok, "speed", texts["speed_ok"].format(days=product.decision_days, days_text=days_text(product.decision_days)), texts["speed_bad"].format(days=product.decision_days, days_text=days_text(product.decision_days)), critical=False)

        if not product.requires_collateral:
            check(True, "collateral", texts["collateral_ok"], "")
        else:
            check(request.has_collateral, "collateral", texts["collateral_have"], texts["collateral_bad"])

        results.append(item)

    # Сначала подходящие, затем по баллам; при равенстве выше продукт с более быстрым решением
    results.sort(key=lambda item: (not item.suitable, -item.score, item.product.decision_days))
    return results
