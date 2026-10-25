"""Справочники, подбор продукта и калькулятор. Доступны без входа: в них нет персональных данных."""

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_config import get_business_config
from app.core.db import get_db
from app.core.errors import AppError
from app.domain.formatting import format_money, format_percent, months_text
from app.domain.payments import ANNUITY, DIFFERENTIATED, payment_schedule, schedule_summary
from app.domain.recommend import RecommendationInput, recommend_products
from app.models import Product
from app.schemas.application import ProductShort
from app.schemas.catalog import (
    CalculatorOut,
    CodeLabel,
    DocumentKindOut,
    FieldOut,
    PaymentTypeOption,
    ProductOut,
    PurposeOut,
    RecommendationOut,
    RecommendRequest,
    ScheduleRow,
)

router = APIRouter(tags=["Справочники и калькулятор"])


def product_to_out(product: Product) -> ProductOut:
    config = get_business_config()
    purposes = []
    for code in product.purposes:
        purpose = config.dictionaries.purpose(code)
        purposes.append(CodeLabel(code=code, label=purpose.label if purpose else code))
    return ProductOut(
        code=product.code,
        name=product.name,
        description=product.description,
        suitable_for=product.suitable_for,
        purposes=purposes,
        min_amount=product.min_amount,
        max_amount=product.max_amount,
        min_term_months=product.min_term_months,
        max_term_months=product.max_term_months,
        base_rate=product.base_rate,
        rate_text=f"от {format_percent(product.base_rate)}% годовых",
        requires_collateral=product.requires_collateral,
        decision_days=product.decision_days,
        required_fields=[FieldOut(field=field, label=config.labels.fields.get(field, field)) for field in product.required_fields],
    )


def active_products(db: Session) -> list[Product]:
    return list(db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.sort_order)))


@router.get("/products", response_model=list[ProductOut], summary="Кредитные продукты с понятным описанием")
def list_products(db: Session = Depends(get_db)):
    return [product_to_out(product) for product in active_products(db)]


@router.post("/products/recommend", response_model=list[RecommendationOut], summary="Подбор продукта по ответам клиента")
def recommend(body: RecommendRequest, db: Session = Depends(get_db)):
    config = get_business_config()
    if config.dictionaries.purpose(body.purpose_code) is None:
        raise AppError("Такой цели кредита нет. Выберите цель из списка.", code="unknown_purpose")
    products_in_db = {product.code: product for product in active_products(db)}
    product_configs = [item for item in config.products.products if item.code in products_in_db]
    results = recommend_products(
        product_configs,
        config.dictionaries,
        config.products.recommendation,
        RecommendationInput(
            purpose_code=body.purpose_code,
            amount=body.amount,
            term_months=body.term_months,
            urgency=body.urgency,
            has_collateral=body.has_collateral,
        ),
    )
    return [
        RecommendationOut(
            product=product_to_out(products_in_db[item.product.code]),
            score=item.score,
            max_score=item.max_score,
            suitable=item.suitable,
            reasons=item.reasons,
            warnings=item.warnings,
        )
        for item in results
    ]


@router.get("/dictionaries/purposes", response_model=list[PurposeOut], summary="Цели финансирования")
def list_purposes():
    return [PurposeOut(**item.model_dump()) for item in get_business_config().dictionaries.purposes]


@router.get("/dictionaries/document-kinds", response_model=list[DocumentKindOut], summary="Виды документов для загрузки")
def list_document_kinds():
    return [DocumentKindOut(**item.model_dump()) for item in get_business_config().dictionaries.document_kinds]


@router.get("/calculator", response_model=CalculatorOut, summary="Предварительный расчёт платежа")
def calculator(
    product: str = Query(description="Код продукта", examples=["working_capital"]),
    amount: Decimal = Query(gt=0, le=1_000_000_000, description="Сумма, ₽", examples=[1500000]),
    term: int = Query(gt=0, le=360, description="Срок, мес.", examples=[24]),
    payment_type: Literal["annuity", "differentiated"] = Query(
        default="annuity", description="annuity — одинаковый платёж каждый месяц, differentiated — платёж уменьшается со временем"
    ),
    db: Session = Depends(get_db),
):
    item = db.get(Product, product)
    if item is None or not item.is_active:
        raise AppError("Такого кредитного продукта нет. Выберите продукт из списка.", code="unknown_product")
    if not item.min_amount <= amount <= item.max_amount:
        raise AppError(
            f"Для продукта «{item.name}» доступна сумма от {format_money(item.min_amount)} до {format_money(item.max_amount)} ₽.",
            code="amount_out_of_range",
            details={"min_amount": float(item.min_amount), "max_amount": float(item.max_amount)},
        )
    if not item.min_term_months <= term <= item.max_term_months:
        raise AppError(
            f"Для продукта «{item.name}» доступен срок от {item.min_term_months} до {item.max_term_months} месяцев.",
            code="term_out_of_range",
            details={"min_term_months": item.min_term_months, "max_term_months": item.max_term_months},
        )
    # Максимальная надбавка среди грейдов, по которым банк может дать предложение
    max_premium = max(rule.rate_premium for rule in get_business_config().decision.grade_rules.values() if rule.decision != "reject")
    texts = get_business_config().labels.calculator
    rows = payment_schedule(amount, item.base_rate, term, payment_type)
    summary = schedule_summary(rows, amount)
    differentiated = payment_type == DIFFERENTIATED
    note_key = "note_differentiated" if differentiated else "note"
    return CalculatorOut(
        product=ProductShort(code=item.code, name=item.name),
        amount=amount,
        term_months=term,
        rate=item.base_rate,
        payment_type=payment_type,
        payment_type_options=[
            PaymentTypeOption(code=ANNUITY, label=texts["type_annuity"]),
            PaymentTypeOption(code=DIFFERENTIATED, label=texts["type_differentiated"]),
        ],
        monthly_payment=summary["first_payment"],
        payment_label=texts["label_differentiated" if differentiated else "label_annuity"],
        payment_caption=texts["caption_differentiated" if differentiated else "caption_annuity"].format(
            last=format_money(summary["last_payment"]), term_text=months_text(term)
        ),
        first_payment=summary["first_payment"],
        last_payment=summary["last_payment"],
        total_payment=summary["total_payment"],
        overpayment=summary["overpayment"],
        note=texts[note_key].format(rate=format_percent(item.base_rate), max_rate=format_percent(item.base_rate + max_premium)),
        schedule=[ScheduleRow(**row) for row in rows],
    )
