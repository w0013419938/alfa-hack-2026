"""Кредитный договор по HTML-шаблону config/contract_template.html (имитация подписания)."""

import html
from datetime import UTC, datetime
from string import Template

from sqlalchemy.orm import Session

from app.core.business_config import get_business_config
from app.core.errors import ConflictError
from app.domain.formatting import format_money, format_percent, months_text
from app.domain.payments import payment_summary
from app.domain.state_machine import get_current_offer
from app.models import Application, Document, User
from app.services.documents import CONTENT_TYPES, store_bytes

CONTRACT_KIND = "contract"


def render_contract(db: Session, application: Application, signer: User | None, signed_at: datetime | None) -> str:
    offer = get_current_offer(db, application.id)
    if offer is None:
        raise ConflictError("По заявке ещё нет предложения банка, договор сформировать нельзя.", code="no_offer")
    summary = payment_summary(offer.amount, offer.rate, offer.term_months)
    company = application.company
    if signed_at:
        signed_text = f"Подписано простой электронной подписью {signed_at:%d.%m.%Y %H:%M} UTC (имитация)."
    else:
        signed_text = "Проект договора. Ещё не подписан."
    values = {
        "number": application.number,
        "date": (signed_at or datetime.now(UTC)).strftime("%d.%m.%Y"),
        "company_name": company.name,
        "company_inn": company.inn,
        "company_ogrn": company.ogrn,
        "signer_name": signer.full_name if signer else application.author.full_name,
        "product_name": application.product.name,
        "amount": format_money(offer.amount),
        "term_months": offer.term_months,
        "term_text": months_text(offer.term_months),
        "rate": format_percent(offer.rate),
        "monthly_payment": format_money(offer.monthly_payment),
        "total_payment": format_money(summary["total_payment"]),
        "overpayment": format_money(summary["overpayment"]),
        "signed_text": signed_text,
    }
    # Экранируем значения, чтобы данные из БД не могли «сломать» HTML
    safe_values = {key: html.escape(str(value)) for key, value in values.items()}
    return Template(get_business_config().contract_template).safe_substitute(safe_values)


def save_signed_contract(db: Session, application: Application, signer: User) -> Document:
    content = render_contract(db, application, signer, signed_at=datetime.now(UTC))
    document = Document(
        application_id=application.id,
        uploaded_by_user_id=None,  # документ сформирован системой
        kind=CONTRACT_KIND,
        original_filename=f"Договор_{application.number}.html",
        stored_path=store_bytes(application.id, content.encode("utf-8"), ".html"),
        content_type=CONTENT_TYPES[".html"],
        size_bytes=len(content.encode("utf-8")),
    )
    db.add(document)
    return document
