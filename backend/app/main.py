"""Точка входа FastAPI-приложения."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html

from app.api import applications, auth, backoffice, catalog, feed, health
from app.core.business_config import get_business_config
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestIdMiddleware
from app.core.settings import get_settings
from app.schemas.common import ErrorResponse
from app.services.dispatcher import dispatcher
from app.services.pipeline import resume_unfinished_applications, start_watchdog

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_business_config()  # если конфиги команды сломаны, падаем сразу с понятной ошибкой
    resume_unfinished_applications(dispatcher)  # добираем заявки, прерванные перезапуском
    stop_watchdog = start_watchdog(dispatcher)  # и дальше раз в минуту ищем застрявшие
    yield
    stop_watchdog.set()
    dispatcher.shutdown()


app = FastAPI(
    title="Умный кредитный кабинет предпринимателя: API",
    version="0.1.0",
    description=(
        "Бэкенд прототипа цифрового кредитного конвейера для малого и микробизнеса.\n\n"
        "**Как начать:** `POST /api/v1/auth/login` с логином `client_good` и паролем `client_good123`, "
        "скопируйте `access_token`, нажмите **Authorize** и вставьте токен. Все учётки перечислены в README.\n\n"
        "Каждый ответ с заявкой содержит `status_label`, `status_description`, `available_actions`, `progress` и `timeline`, "
        "так что фронту не нужно ничего вычислять самому."
    ),
    lifespan=lifespan,
    docs_url=None,  # Swagger UI и ReDoc отдаём ниже с закреплёнными версиями
    redoc_url=None,
)

# Страницы документации загружают JS/CSS в браузере с CDN. Версии закреплены, чтобы вид не менялся сам по себе.
SWAGGER_UI_VERSION = "5.17.14"
REDOC_VERSION = "2.1.5"


@app.get("/docs", include_in_schema=False)
def swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title}, Swagger UI",
        swagger_js_url=f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui-bundle.js",
        swagger_css_url=f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui.css",
        swagger_ui_parameters={"persistAuthorization": True},
    )


@app.get("/redoc", include_in_schema=False)
def redoc():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title}, ReDoc",
        redoc_js_url=f"https://cdn.jsdelivr.net/npm/redoc@{REDOC_VERSION}/bundles/redoc.standalone.js",
    )


# Порядок важен: добавленный последним middleware считается внешним. CORS снаружи, чтобы его заголовки
# были и у ответа 500, который формирует RequestIdMiddleware.
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
register_error_handlers(app)

API_PREFIX = "/api/v1"

# Все ошибки приходят в одном формате {"error": {"code", "message", "details"}}, и это описано в схеме API
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
