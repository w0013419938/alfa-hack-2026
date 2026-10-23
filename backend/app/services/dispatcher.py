"""Диспетчер фоновой обработки заявок.

Сейчас заявки обрабатываются в пуле потоков внутри процесса бэкенда.
Чтобы вынести обработку в очередь (RabbitMQ, Celery, Kafka), достаточно написать
другой класс с методом dispatch(application_id) — остальной код менять не нужно.
"""

import contextvars
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


class PipelineDispatcher(Protocol):
    def dispatch(self, application_id: uuid.UUID) -> None: ...


class ThreadPoolDispatcher:
    def __init__(self, workers: int):
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="pipeline")

    def dispatch(self, application_id: uuid.UUID) -> None:
        from app.services.pipeline import run_pipeline  # локальный импорт, чтобы избежать цикла

        # Копируем контекст, чтобы request id попал в логи фоновых шагов
        context = contextvars.copy_context()
        self._executor.submit(context.run, run_pipeline, application_id)
        logger.info("Заявка поставлена в обработку", extra={"application_id": str(application_id)})

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


class InlineDispatcher:
    """Обрабатывает заявку сразу, в текущем потоке и без пауз. Используется при загрузке демо-данных."""

    def dispatch(self, application_id: uuid.UUID) -> None:
        from app.services.pipeline import run_pipeline

        run_pipeline(application_id, step_delay=0)


dispatcher = ThreadPoolDispatcher(get_settings().pipeline_workers)


def get_dispatcher() -> PipelineDispatcher:
    """Зависимость FastAPI (в тестах её можно подменить)."""
    return dispatcher
