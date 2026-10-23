"""Пайплайн автоматической обработки заявки (наполняется на этапе 6)."""

import logging
import uuid

logger = logging.getLogger(__name__)


def run_pipeline(application_id: uuid.UUID) -> None:
    logger.info("Пайплайн пока не реализован", extra={"application_id": str(application_id)})
