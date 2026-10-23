"""SQLAlchemy-модели. Импортируем все модели здесь, чтобы Alembic видел их метаданные."""

from app.models.base import Base
from app.models.company import Company
from app.models.user import User
from app.models.product import Product
from app.models.application import Application, ApplicationEvent
from app.models.checks import ExternalCheck, ScoringResult
from app.models.offer import Offer
from app.models.info_request import InfoRequest
from app.models.document import Document

__all__ = [
    "Base",
    "Company",
    "User",
    "Product",
    "Application",
    "ApplicationEvent",
    "ExternalCheck",
    "ScoringResult",
    "Offer",
    "InfoRequest",
    "Document",
]
