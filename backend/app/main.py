"""Точка входа FastAPI-приложения."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import applications, auth, backoffice, catalog, health
from app.core.business_config import get_business_config
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestIdMiddleware
from app.core.settings import get_settings
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
    description="Бэкенд прототипа цифрового кредитного конвейера для малого и микробизнеса.",
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
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(catalog.router, prefix=API_PREFIX)
app.include_router(applications.router, prefix=API_PREFIX)
app.include_router(backoffice.router, prefix=API_PREFIX)
