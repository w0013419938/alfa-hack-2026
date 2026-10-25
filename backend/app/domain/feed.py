"""Персональная лента подсказок: отбор по правилам config/feed.yaml.

Подсказка показывается, если выполнены ВСЕ её условия (отрасль, тип компании, статус и продукт текущей заявки).
Чем больше условий совпало, тем выше подсказка в ленте. У каждой есть объяснение «почему показано».
"""

from dataclasses import dataclass

from app.core.business_config import FeedFile


@dataclass
class FeedContext:
    okved: str
    industry: str
    company_type: str
    company_type_label: str
    application_status: str | None  # статус текущей заявки (None, если заявок нет)
    application_status_label: str | None
    product_code: str | None
    product_name: str | None


@dataclass
class FeedEntry:
    id: str
    title: str
    text: str
    tag: str
    reason: str
    score: int


def matched_conditions(conditions: dict, context: FeedContext) -> list[str] | None:
    """Список совпавших условий или None, если хотя бы одно условие не выполнено."""
    matched = []
    okved_prefixes = conditions.get("okved_prefixes")
    if okved_prefixes:
        if not any(context.okved.startswith(prefix) for prefix in okved_prefixes):
            return None
        matched.append("okved")
    company_types = conditions.get("company_types")
    if company_types:
        if context.company_type not in company_types:
            return None
        matched.append("company_type")
    statuses = conditions.get("application_statuses")
    if statuses:
        if context.application_status not in statuses:
            return None
        matched.append("application_status")
    products = conditions.get("product_codes")
    if products:
        if context.product_code not in products:
            return None
        matched.append("product")
    return matched


def build_feed(items: list[dict], context: FeedContext, config: FeedFile) -> list[FeedEntry]:
    values = {
        "industry": context.industry,
        "company_type": context.company_type_label,
        "status_label": context.application_status_label,
        "product_name": context.product_name,
    }
    entries = []
    for item in items:
        matched = matched_conditions(item.get("conditions") or {}, context)
        if matched is None:
            continue
        reason_keys = matched or ["general"]
        reason = "; ".join(config.reasons[key].format(**values) for key in reason_keys)
        score = sum(config.weights.get(key, 0) for key in matched) + int(item.get("priority", 0))
        entries.append(FeedEntry(id=item["id"], title=item["title"], text=item["text"], tag=item["tag"], reason=reason, score=score))

    entries.sort(key=lambda entry: entry.score, reverse=True)
    return entries[: config.max_items]
