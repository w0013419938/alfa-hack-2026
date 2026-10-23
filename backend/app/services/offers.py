"""Создание предложений и запросов уточнений (используют и пайплайн, и сотрудник банка)."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_config import get_business_config
from app.domain.decision import OfferTerms
from app.models import Application, InfoRequest, Offer
from app.models.offer import OFFER_ACTIVE, OFFER_SUPERSEDED


def create_offer(db: Session, application: Application, terms: OfferTerms, created_by_user_id: uuid.UUID | None = None) -> Offer:
    # Старые действующие предложения заменяются новым
    for old in db.scalars(select(Offer).where(Offer.application_id == application.id, Offer.status == OFFER_ACTIVE)):
        old.status = OFFER_SUPERSEDED
    offer = Offer(
        application_id=application.id,
        offer_type=terms.offer_type,
        amount=terms.amount,
        term_months=terms.term_months,
        rate=terms.rate,
        monthly_payment=terms.monthly_payment,
        valid_until=datetime.now(UTC) + timedelta(days=get_business_config().decision.offer_valid_days),
        status=OFFER_ACTIVE,
        created_by_user_id=created_by_user_id,
    )
    db.add(offer)
    return offer


def create_info_request(
    db: Session,
    application: Application,
    comment: str,
    fields: list[dict] | None = None,
    documents: list[str] | None = None,
    created_by_type: str = "system",
    created_by_user_id: uuid.UUID | None = None,
) -> InfoRequest:
    # Предыдущие открытые запросы закрываем: актуален только последний
    for old in db.scalars(select(InfoRequest).where(InfoRequest.application_id == application.id, InfoRequest.is_open.is_(True))):
        old.is_open = False
    info_request = InfoRequest(
        application_id=application.id,
        requested_fields=fields or [],
        requested_documents=documents or [],
        comment=comment,
        created_by_type=created_by_type,
        created_by_user_id=created_by_user_id,
        is_open=True,
    )
    db.add(info_request)
    return info_request
