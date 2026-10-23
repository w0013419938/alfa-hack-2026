"""Юнит-тесты: проверка анкеты, подбор продукта, лента подсказок, ограничение попыток входа."""

from decimal import Decimal
from types import SimpleNamespace

from app.core.business_config import get_business_config
from app.core.rate_limit import LoginRateLimiter
from app.domain.feed import FeedContext, build_feed
from app.domain.recommend import RecommendationInput, recommend_products
from app.domain.validation import validate_application

CONFIG = get_business_config()
PRODUCT = CONFIG.product("working_capital")
VALID_INN = "7701001012"


def product_row(config_product, is_active=True):
    return SimpleNamespace(**config_product.model_dump(), is_active=is_active)


def application(**overrides):
    data = {
        "amount": Decimal(1_500_000),
        "term_months": 24,
        "purpose_code": PRODUCT.purposes[0],
        "purpose_comment": None,
        "collateral_description": None,
        "monthly_revenue": Decimal(800_000),
        "monthly_expenses": Decimal(500_000),
        "current_loan_payments": Decimal(0),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def fields_with_problems(problems):
    return {problem.field for problem in problems}


def test_complete_application_has_no_problems():
    assert validate_application(application(), product_row(PRODUCT), VALID_INN, CONFIG) == []


def test_missing_required_fields_are_listed():
    problems = validate_application(application(monthly_revenue=None, term_months=None), product_row(PRODUCT), VALID_INN, CONFIG)
    assert {"monthly_revenue", "term_months"} <= fields_with_problems(problems)


def test_amount_and_term_out_of_product_range():
    app = application(amount=PRODUCT.max_amount + 1, term_months=PRODUCT.max_term_months + 1)
    assert {"amount", "term_months"} <= fields_with_problems(validate_application(app, product_row(PRODUCT), VALID_INN, CONFIG))


def test_purpose_not_suitable_for_product():
    wrong_purpose = next(item.code for item in CONFIG.dictionaries.purposes if item.code not in PRODUCT.purposes)
    problems = validate_application(application(purpose_code=wrong_purpose), product_row(PRODUCT), VALID_INN, CONFIG)
    assert "purpose_code" in fields_with_problems(problems)


def test_other_purpose_requires_comment():
    product = CONFIG.product("express")
    purpose = next(item for item in CONFIG.dictionaries.purposes if item.requires_comment and item.code in product.purposes)
    problems = validate_application(application(purpose_code=purpose.code), product_row(product), VALID_INN, CONFIG)
    assert "purpose_comment" in fields_with_problems(problems)


def test_collateral_required_for_secured_product():
    product = next(item for item in CONFIG.products.products if "collateral_description" in item.required_fields)
    app = application(purpose_code=product.purposes[0], amount=product.min_amount, term_months=product.min_term_months)
    assert "collateral_description" in fields_with_problems(validate_application(app, product_row(product), VALID_INN, CONFIG))


def test_invalid_company_inn_is_reported():
    problems = validate_application(application(), product_row(PRODUCT), "7707083890", CONFIG)
    assert any(problem.field is None for problem in problems)


def test_unreasonable_numbers():
    app = application(monthly_expenses=Decimal(900_000), current_loan_payments=Decimal(900_000))
    assert {"monthly_expenses", "current_loan_payments"} <= fields_with_problems(validate_application(app, product_row(PRODUCT), VALID_INN, CONFIG))


def test_inactive_product():
    problems = validate_application(application(), product_row(PRODUCT, is_active=False), VALID_INN, CONFIG)
    assert fields_with_problems(problems) == {"product_code"}


def test_recommendation_puts_suitable_product_first():
    request = RecommendationInput(purpose_code="equipment", amount=Decimal(2_000_000), term_months=36, urgency="month", has_collateral=True)
    results = recommend_products(CONFIG.products.products, CONFIG.dictionaries, CONFIG.products.recommendation, request)
    assert results[0].suitable
    assert "equipment" in results[0].product.purposes
    assert results[0].reasons
    unsuitable = [item for item in results if not item.suitable]
    assert all(item.warnings for item in unsuitable)


def test_recommendation_without_collateral_excludes_secured_products():
    request = RecommendationInput(purpose_code="equipment", amount=Decimal(2_000_000), term_months=36, urgency="month", has_collateral=False)
    results = recommend_products(CONFIG.products.products, CONFIG.dictionaries, CONFIG.products.recommendation, request)
    for item in results:
        if item.product.requires_collateral:
            assert not item.suitable


FEED_ITEMS = [
    {"id": "general", "title": "t", "text": "t", "tag": "t", "priority": 1, "conditions": {}},
    {"id": "retail", "title": "t", "text": "t", "tag": "t", "priority": 1, "conditions": {"okved_prefixes": ["47"]}},
    {"id": "ie", "title": "t", "text": "t", "tag": "t", "priority": 1, "conditions": {"company_types": ["IE"]}},
    {"id": "needs-info", "title": "t", "text": "t", "tag": "t", "priority": 1, "conditions": {"application_statuses": ["NEEDS_INFO"]}},
    {"id": "retail-draft", "title": "t", "text": "t", "tag": "t", "priority": 1, "conditions": {"okved_prefixes": ["47"], "application_statuses": ["DRAFT"]}},
]


def feed_context(**overrides):
    data = {
        "okved": "47.11",
        "industry": "Торговля",
        "company_type": "LLC",
        "company_type_label": "ООО",
        "application_status": "NEEDS_INFO",
        "application_status_label": "Нужны уточнения",
        "product_code": "express",
        "product_name": "Экспресс",
    }
    data.update(overrides)
    return FeedContext(**data)


def test_feed_shows_only_items_with_all_conditions_matched():
    ids = [entry.id for entry in build_feed(FEED_ITEMS, feed_context(), CONFIG.feed)]
    assert set(ids) == {"general", "retail", "needs-info"}
    assert ids[0] == "needs-info"  # статус заявки весит больше всего
    assert ids[-1] == "general"


def test_feed_reason_explains_match():
    entries = {entry.id: entry for entry in build_feed(FEED_ITEMS, feed_context(company_type="IE", company_type_label="ИП"), CONFIG.feed)}
    assert "ИП" in entries["ie"].reason
    assert "Торговля" in entries["retail"].reason
    assert entries["general"].reason == CONFIG.feed.reasons["general"]


def test_feed_respects_max_items():
    many = [{**FEED_ITEMS[0], "id": f"item{index}"} for index in range(CONFIG.feed.max_items + 5)]
    assert len(build_feed(many, feed_context(), CONFIG.feed)) == CONFIG.feed.max_items


def test_login_rate_limiter_blocks_after_limit_and_resets():
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=60)
    assert not limiter.is_blocked("ip:user")
    limiter.register_failure("ip:user")
    limiter.register_failure("ip:user")
    assert limiter.is_blocked("ip:user")
    assert not limiter.is_blocked("ip:other")
    limiter.reset("ip:user")
    assert not limiter.is_blocked("ip:user")
