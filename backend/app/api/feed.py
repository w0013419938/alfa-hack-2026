"""Персональная лента подсказок и новостей для клиента."""

import json
from functools import lru_cache

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_client
from app.core.business_config import get_business_config
from app.core.db import get_db
from app.core.settings import get_settings
from app.domain.feed import FeedContext, build_feed
from app.domain.statuses import FINAL_STATUSES
from app.models import Application, User

router = APIRouter(tags=["Лента подсказок"])


class FeedItemOut(BaseModel):
    id: str
    title: str
    text: str
    tag: str
    reason: str  # почему показано


@lru_cache
def load_feed_items() -> list[dict]:
    with (get_settings().seed_dir / "feed_items.json").open(encoding="utf-8") as file:
        return json.load(file)["items"]


def current_application(db: Session, user: User) -> Application | None:
    """Текущая заявка: последняя незавершённая, а если таких нет — просто последняя."""
    applications = db.scalars(select(Application).where(Application.company_id == user.company_id).order_by(Application.created_at.desc())).all()
    active = [item for item in applications if item.status not in FINAL_STATUSES]
    return (active or applications or [None])[0]


@router.get(
    "/feed",
    response_model=list[FeedItemOut],
    summary="Персональная лента подсказок",
    description="Подборка по отрасли (ОКВЭД), типу компании, статусу и продукту текущей заявки. У каждой подсказки есть `reason` — почему она показана.",
)
def get_feed(user: User = Depends(get_current_client), db: Session = Depends(get_db)):
    config = get_business_config()
    company = user.company
    application = current_application(db, user)
    context = FeedContext(
        okved=company.okved,
        industry=company.industry,
        company_type=company.company_type,
        company_type_label=config.dictionaries.company_types.get(company.company_type, company.company_type),
        application_status=application.status if application else None,
        application_status_label=config.status_label(application.status) if application else None,
        product_code=application.product_code if application else None,
        product_name=application.product.name if application else None,
    )
    entries = build_feed(load_feed_items(), context, config.feed)
    return [FeedItemOut(id=entry.id, title=entry.title, text=entry.text, tag=entry.tag, reason=entry.reason) for entry in entries]
