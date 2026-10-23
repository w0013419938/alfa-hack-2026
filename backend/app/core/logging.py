"""Структурированные логи в формате JSON с request id.

Правило: в логи не пишем персональные данные (ФИО, ИНН, телефоны, суммы по конкретным людям).
Пишем только идентификаторы (id заявки, id пользователя), статусы и технические детали.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# Request id текущего запроса. Пайплайн копирует контекст, поэтому id виден и в фоновых шагах.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Поля, которые можно передать через logger.info(..., extra={...})
EXTRA_FIELDS = (
    "application_id",
    "user_id",
    "action",
    "from_status",
    "to_status",
    "actor",
    "check_type",
    "attempt",
    "status_code",
    "method",
    "path",
    "duration_ms",
    "error",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "time": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for field in EXTRA_FIELDS:
            if hasattr(record, field):
                data[field] = getattr(record, field)
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # uvicorn настраивает свои логгеры сам — перенаправляем их в общий JSON-формат
    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
    # Журнал запросов пишет наш RequestIdMiddleware; access-лог uvicorn содержит IP-адреса — отключаем
    logging.getLogger("uvicorn.access").disabled = True
    # Подробные логи HTTP-клиента не нужны (в них есть адреса запросов с ИНН)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
