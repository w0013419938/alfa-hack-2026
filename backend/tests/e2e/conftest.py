"""Фикстуры e2e-тестов: чистая тестовая база, миграции, seed и клиент API.

Тестовая база (<основная>_test) пересоздаётся один раз за запуск тестов.
Внешние сервисы настоящие: mock-external из docker compose.
"""

import os
import time

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.settings import BACKEND_DIR

# Статусы, на которых автоматическая обработка останавливается и ждёт человека
WAITING_STATUSES = {"NEEDS_INFO", "MANUAL_REVIEW", "OFFER_SENT", "REJECTED", "ISSUED", "CANCELLED", "CLIENT_DECLINED", "DRAFT"}

# Тело заявки из docs/test-scenarios.md, одно и то же для всех демо-клиентов
STANDARD_APPLICATION = {
    "product_code": "working_capital",
    "amount": 1500000,
    "term_months": 24,
    "purpose_code": "working_capital",
    "monthly_revenue": 800000,
    "monthly_expenses": 550000,
    "current_loan_payments": 0,
}


def recreate_test_database() -> None:
    test_url = make_url(os.environ["DATABASE_URL"])
    admin_url = test_url.set(database="postgres")
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{test_url.database}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    engine.dispose()


@pytest.fixture(scope="session")
def client():
    recreate_test_database()
    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(alembic_config, "head")

    from app.seed import run_seed

    run_seed()

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


class Api:
    """Небольшая обёртка над клиентом API, чтобы тесты читались как сценарии."""

    def __init__(self, client: TestClient, login: str):
        self.client = client
        response = client.post("/api/v1/auth/login", json={"login": login, "password": f"{login}123"})
        assert response.status_code == 200, response.text
        self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    def get(self, path: str, **kwargs):
        return self.client.get(f"/api/v1{path}", headers=self.headers, **kwargs)

    def post(self, path: str, **kwargs):
        return self.client.post(f"/api/v1{path}", headers=self.headers, **kwargs)

    def patch(self, path: str, **kwargs):
        return self.client.patch(f"/api/v1{path}", headers=self.headers, **kwargs)

    def create_application(self, **overrides) -> dict:
        response = self.post("/applications", json={**STANDARD_APPLICATION, **overrides})
        assert response.status_code == 201, response.text
        return check_application_shape(response.json())

    def action(self, application_id: str, action: str, expected_status_code: int = 200, **body) -> dict:
        response = self.post(f"/applications/{application_id}/actions/{action}", json=body or None)
        assert response.status_code == expected_status_code, response.text
        return response.json()

    def employee_action(self, application_id: str, action: str, expected_status_code: int = 200, **body) -> dict:
        response = self.post(f"/backoffice/applications/{application_id}/actions/{action}", json=body)
        assert response.status_code == expected_status_code, response.text
        return response.json()

    def application(self, application_id: str) -> dict:
        response = self.get(f"/applications/{application_id}")
        assert response.status_code == 200, response.text
        return check_application_shape(response.json())

    def wait_until_processed(self, application_id: str, timeout: float = 30) -> dict:
        """Ждём, пока фоновая обработка доведёт заявку до статуса, где нужен человек."""
        deadline = time.monotonic() + timeout
        while True:
            data = self.application(application_id)
            if data["status"] in WAITING_STATUSES:
                return data
            assert time.monotonic() < deadline, f"Заявка зависла в статусе {data['status']}"
            time.sleep(0.2)

    def upload(self, application_id: str, kind: str, filename: str, content: bytes, expected_status_code: int = 201) -> dict:
        response = self.post(f"/applications/{application_id}/documents", data={"kind": kind}, files={"file": (filename, content)})
        assert response.status_code == expected_status_code, response.text
        return response.json()


def check_application_shape(data: dict) -> dict:
    """Каждый ответ с заявкой обязан содержать всё, что нужно фронту."""
    for key in ("status", "status_label", "status_description", "available_actions", "timeline", "progress"):
        assert key in data, f"В ответе нет поля {key}"
    assert data["status_label"] and data["status_description"]
    assert data["timeline"], "Таймлайн не может быть пустым: у заявки всегда есть событие создания"
    for action in data["available_actions"]:
        assert action["code"] and action["label"]
    assert [step["code"] for step in data["progress"]][0] == "submitted"
    assert all(step["label"] and step["state_label"] for step in data["progress"])
    return data


def action_codes(data: dict, only_enabled: bool = True) -> set[str]:
    return {item["code"] for item in data["available_actions"] if item["enabled"] or not only_enabled}


@pytest.fixture
def api(client):
    """api("client_good") даёт клиент API от имени пользователя."""
    return lambda login: Api(client, login)


PDF = b"%PDF-1.4\n% test document\n%%EOF\n"
