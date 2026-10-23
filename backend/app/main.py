"""Точка входа FastAPI-приложения."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import applications, auth, backoffice, catalog, feed, health
from app.core.business_config import get_business_config
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestIdMiddleware
from app.core.settings import get_settings
from app.schemas.common import ErrorResponse
from app.services.dispatcher import dispatcher
from app.services.pipeline import resume_unfinished_applications

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_business_config()  # если конфиги команды сломаны — падаем сразу с понятной ошибкой
    resume_unfinished_applications(dispatcher)
    yield
    dispatcher.shutdown()


app = FastAPI(
    title="Умный кредитный кабинет предпринимателя — API",
    version="0.1.0",
    description=(
        "Бэкенд прототипа цифрового кредитного конвейера для малого и микробизнеса.\n\n"
        "**Как начать:** `POST /api/v1/auth/login` с логином `client_good` и паролем `client_good123`, "
        "скопируйте `access_token`, нажмите **Authorize** и вставьте токен. Все учётки — в README.\n\n"
        "Каждый ответ с заявкой содержит `status_label`, `status_description`, `available_actions` и `timeline` — "
        "фронту не нужно ничего вычислять самому."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestIdMiddleware)
register_error_handlers(app)

API_PREFIX = "/api/v1"

# Все ошибки приходят в одном формате {"error": {"code", "message", "details"}} — описываем это в схеме API
ERROR_RESPONSES = {
    status_code: {"model": ErrorResponse, "description": description}
    for status_code, description in {
        400: "Некорректный запрос (например, сумма вне лимита продукта)",
        401: "Нужно войти в систему",
        403: "Недостаточно прав",
        404: "Не найдено",
        409: "Действие сейчас недоступно (статус заявки или версия изменились)",
        422: "Ошибка проверки входных данных",
    }.items()
}

app.include_router(health.router, prefix=API_PREFIX)
for router in (auth.router, catalog.router, applications.router, backoffice.router, feed.router):
    app.include_router(router, prefix=API_PREFIX, responses=ERROR_RESPONSES)
