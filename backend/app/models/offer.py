import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, uuid_pk

OFFER_AS_REQUESTED = "as_requested"
OFFER_COUNTER = "counter_offer"

OFFER_ACTIVE = "active"
OFFER_ACCEPTED = "accepted"
OFFER_DECLINED = "declined"
OFFER_SUPERSEDED = "superseded"  # заменено новым предложением


class Offer(Base):
    """Кредитное предложение клиенту."""

    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    offer_type: Mapped[str] = mapped_column(String(16), nullable=False)  # as_requested / counter_offer
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # % годовых
    monthly_payment: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=OFFER_ACTIVE)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # None, если предложение создала система
    created_at: Mapped[datetime] = created_at_column()
