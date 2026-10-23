"""Служебные эндпоинты для Docker и оркестратора."""

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.settings import get_settings

router = APIRouter(tags=["Служебное"])


@router.get("/health", summary="Liveness: процесс жив")
def health():
    return {"status": "ok"}


@router.get("/ready", summary="Readiness: доступны база данных и внешние сервисы")
def ready():
    checks = {}
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    try:
        response = httpx.get(f"{get_settings().external_api_url}/health", timeout=2.0)
        checks["mock_external"] = "ok" if response.status_code == 200 else "error"
    except httpx.HTTPError:
        checks["mock_external"] = "error"

    is_ready = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={"status": "ok" if is_ready else "not_ready", "checks": checks},
    )
