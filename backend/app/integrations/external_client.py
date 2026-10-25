"""Клиент внешних сервисов: ЕГРЮЛ/ЕГРИП и бюро кредитных историй (БКИ).

ExternalDataClient это интерфейс (что умеет клиент), HttpExternalDataClient его реализация через HTTP.
Сейчас HTTP-реализация ходит в локальный mock-external; в продакшене её заменят клиенты настоящих
сервисов с тем же интерфейсом.

Надёжность:
- таймаут на каждую попытку (EXTERNAL_TIMEOUT_SECONDS);
- повтор при таймауте, обрыве связи и ответах 5xx/429 (EXTERNAL_MAX_ATTEMPTS попыток);
- пауза между попытками растёт: 0.5 с, 1 с, 2 с ... (EXTERNAL_BACKOFF_SECONDS × 2^номер);
- клиент никогда не бросает исключение наружу, а возвращает результат со статусом ok / error / timeout,
  чтобы пайплайн мог отправить заявку на ручное рассмотрение, а не упасть.
"""

import logging
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.logging import request_id_var
from app.core.settings import get_settings
from app.models.checks import CHECK_BKI, CHECK_EGRUL, CHECK_ERROR, CHECK_OK, CHECK_TIMEOUT

logger = logging.getLogger(__name__)

# На эти ответы повтор не поможет: это ошибка в запросе, а не временный сбой
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404, 422}


@dataclass
class ExternalCallResult:
    check_type: str
    status: str  # ok / error / timeout
    request: dict
    data: dict | None = None
    error_message: str | None = None
    attempts: int = 1
    duration_ms: int = 0


class ExternalDataClient(Protocol):
    def get_egrul(self, inn: str) -> ExternalCallResult: ...

    def get_bki_report(self, inn: str) -> ExternalCallResult: ...


class HttpExternalDataClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        max_attempts: int,
        backoff_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max(1, max_attempts)
        self.backoff_seconds = backoff_seconds
        self.transport = transport  # для тестов: подмена сетевого слоя

    def get_egrul(self, inn: str) -> ExternalCallResult:
        result = self._get(CHECK_EGRUL, f"/egrul/{inn}", params=None, request={"inn": inn})
        # «Организация не найдена» это ответ реестра, а не сбой: проверка успешна, компании нет
        if result.status == CHECK_ERROR and result.error_message == "HTTP 404":
            result.status = CHECK_OK
            result.data = {"inn": inn, "not_found": True}
            result.error_message = None
        return result

    def get_bki_report(self, inn: str) -> ExternalCallResult:
        return self._get(CHECK_BKI, "/bki/report", params={"inn": inn}, request={"inn": inn})

    def _get(self, check_type: str, path: str, params: dict | None, request: dict) -> ExternalCallResult:
        started = time.perf_counter()
        last_status = CHECK_ERROR
        last_error = "Нет ответа"
        attempt = 0
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds, transport=self.transport) as client:
            for attempt in range(1, self.max_attempts + 1):
                try:
                    response = client.get(path, params=params, headers={"X-Request-ID": request_id_var.get()})
                    if response.status_code == 200:
                        return ExternalCallResult(
                            check_type=check_type,
                            status=CHECK_OK,
                            request=request,
                            data=response.json(),
                            attempts=attempt,
                            duration_ms=self._elapsed_ms(started),
                        )
                    last_status, last_error = CHECK_ERROR, f"HTTP {response.status_code}"
                    if response.status_code in NON_RETRYABLE_STATUS_CODES:
                        break
                except httpx.TimeoutException:
                    last_status, last_error = CHECK_TIMEOUT, f"Нет ответа за {self.timeout_seconds} с"
                except (httpx.TransportError, ValueError) as error:
                    # ValueError значит, что ответ пришёл, но это не JSON
                    last_status, last_error = CHECK_ERROR, f"Ошибка соединения: {type(error).__name__}"

                logger.warning(
                    "Внешний сервис не ответил, попытка не удалась",
                    extra={"check_type": check_type, "attempt": attempt, "error": last_error},
                )
                if attempt < self.max_attempts:
                    time.sleep(self.backoff_seconds * 2 ** (attempt - 1))

        return ExternalCallResult(
            check_type=check_type,
            status=last_status,
            request=request,
            error_message=last_error,
            attempts=attempt,
            duration_ms=self._elapsed_ms(started),
        )

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)


def get_external_client() -> ExternalDataClient:
    settings = get_settings()
    return HttpExternalDataClient(
        base_url=settings.external_api_url,
        timeout_seconds=settings.external_timeout_seconds,
        max_attempts=settings.external_max_attempts,
        backoff_seconds=settings.external_backoff_seconds,
    )
