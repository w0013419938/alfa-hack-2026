"""Мок внешних систем: ЕГРЮЛ/ЕГРИП и бюро кредитных историй (БКИ).

Данные берутся из external_mocks.json по ИНН. Для неизвестного ИНН ответ генерируется
детерминированно из самого ИНН (один и тот же ИНН всегда даёт один и тот же ответ).

Режимы сбоя (поле "failure_mode" в external_mocks.json) нужны для демонстрации отказоустойчивости:
- "timeout": сервис «зависает» дольше, чем ждёт клиент;
- "error": сервис отвечает 500;
- "flaky": каждый нечётный запрос по этому ИНН падает с 503, чётный проходит (видно ретраи).
"""

import hashlib
import json
import logging
import os
import threading
import time
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

DATA_PATH = Path(os.getenv("MOCK_DATA_PATH", "/app/data/external_mocks.json"))
TIMEOUT_SLEEP_SECONDS = float(os.getenv("MOCK_TIMEOUT_SLEEP_SECONDS", "10"))

logging.basicConfig(level=logging.INFO, format='{"level": "%(levelname)s", "message": "%(message)s"}')
logger = logging.getLogger("mock-external")

app = FastAPI(title="Mock External: ЕГРЮЛ/ЕГРИП и БКИ", version="0.1.0")

# Счётчик запросов по (тип, ИНН) для режима "flaky"
_call_counter: dict[tuple[str, str], int] = {}
_counter_lock = threading.Lock()


def load_data() -> dict:
    with DATA_PATH.open(encoding="utf-8") as file:
        data = json.load(file)
    # Ключи, начинающиеся с "_", это комментарии в файле
    return {key: value for key, value in data.items() if not key.startswith("_")}


MOCK_DATA = load_data()


def validate_inn(inn: str) -> None:
    if not inn.isdigit() or len(inn) not in (10, 12):
        raise HTTPException(status_code=400, detail="ИНН должен состоять из 10 или 12 цифр")


def seed_number(inn: str, salt: str) -> int:
    """Детерминированное «случайное» число из ИНН."""
    return int(hashlib.sha256(f"{inn}:{salt}".encode()).hexdigest(), 16)


def apply_failure_mode(kind: str, inn: str, section: dict) -> JSONResponse | None:
    mode = section.get("failure_mode")
    if mode == "timeout":
        time.sleep(TIMEOUT_SLEEP_SECONDS)
        return JSONResponse(status_code=504, content={"error": "timeout"})
    if mode == "error":
        return JSONResponse(status_code=500, content={"error": "internal error"})
    if mode == "flaky":
        with _counter_lock:
            count = _call_counter.get((kind, inn), 0) + 1
            _call_counter[(kind, inn)] = count
        if count % 2 == 1:
            return JSONResponse(status_code=503, content={"error": "temporarily unavailable"})
    return None


def generate_egrul(inn: str) -> dict:
    is_ie = len(inn) == 12
    age_days = 400 + seed_number(inn, "age") % 3000
    return {
        "inn": inn,
        "ogrn": str(300000000000000 + seed_number(inn, "ogrn") % 99999999999999)[: 15 if is_ie else 13],
        "company_type": "IE" if is_ie else "LLC",
        "name": f"{'ИП' if is_ie else 'ООО'} «Компания {inn[-4:]}»",
        "status": "active",
        "registration_date": (date(2026, 1, 1) - timedelta(days=age_days)).isoformat(),
        "okved": ["47.11", "56.10", "62.01", "43.21", "46.90"][seed_number(inn, "okved") % 5],
        "region": "г. Москва",
        "director": {"full_name": "Иванов Иван Иванович", "position": "Индивидуальный предприниматель" if is_ie else "Генеральный директор"},
    }


def generate_bki(inn: str) -> dict:
    loans_count = seed_number(inn, "loans") % 3
    loans = []
    for index in range(loans_count):
        amount = 300000 + seed_number(inn, f"amount{index}") % 2000000
        loans.append(
            {
                "type": "Кредит",
                "amount": amount,
                "balance": round(amount * 0.6),
                "monthly_payment": round(amount / 24),
                "current_overdue_days": 0,
            }
        )
    return {
        "inn": inn,
        "rating": 600 + seed_number(inn, "rating") % 220,
        "active_loans": loans,
        "overdue_history": {"count": seed_number(inn, "overdue") % 2, "max_days": (seed_number(inn, "days") % 2) * 10},
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/egrul/{inn}", summary="Выписка из ЕГРЮЛ/ЕГРИП")
def get_egrul(inn: str):
    validate_inn(inn)
    record = MOCK_DATA.get(inn, {}).get("egrul")
    if record is not None:
        failure = apply_failure_mode("egrul", inn, record)
        if failure:
            return failure
        if record.get("not_found"):
            raise HTTPException(status_code=404, detail="Организация не найдена")
        return {"inn": inn, **{key: value for key, value in record.items() if key != "failure_mode"}}
    return generate_egrul(inn)


@app.get("/bki/report", summary="Кредитный отчёт из БКИ")
def get_bki_report(inn: str = Query(...)):
    validate_inn(inn)
    record = MOCK_DATA.get(inn, {}).get("bki")
    if record is not None:
        failure = apply_failure_mode("bki", inn, record)
        if failure:
            return failure
        return {"inn": inn, **{key: value for key, value in record.items() if key != "failure_mode"}}
    return generate_bki(inn)
