"""Middleware: request id и журнал запросов."""

import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import request_id_var

logger = logging.getLogger("app.request")

# Принимаем request id от клиента, только если он «безопасный» (буквы, цифры, дефисы)
SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9\-]{8,64}$")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if SAFE_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response
        finally:
            # Healthcheck Docker приходит каждые несколько секунд — не засоряем им журнал.
            # Пишем только метод, путь и статус: в query-параметрах могут быть данные клиента.
            if not request.url.path.endswith("/health"):
                logger.info(
                    "HTTP запрос",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    },
                )
            request_id_var.reset(token)
