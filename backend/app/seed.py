"""Загрузка справочников и демо-данных: python -m app.seed

Запускается автоматически при старте контейнера (start.sh) и безопасна для повторного запуска:
- продукты обновляются из config/products.yaml при каждом запуске (конфиг — источник истины);
- компании и пользователи добавляются, только если их ещё нет (по ИНН и логину);
- демо-заявки создаются, только если у компании ещё нет заявок.
Чтобы перезалить демо-данные с нуля: docker compose down -v && docker compose up --build
"""

import json
import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.business_config import get_business_config
from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.core.security import hash_password
from app.core.settings import get_settings
from app.models import Application, Company, Product, User
from app.schemas.application import ApplicationCreate
from app.schemas.backoffice import EmployeeActionRequest
from app.services.applications import create_draft, perform_client_action
from app.services.backoffice import perform_employee_action
from app.services.dispatcher import InlineDispatcher

logger = logging.getLogger("app.seed")

# Любое число: по нему PostgreSQL выдаёт блокировку, чтобы два экземпляра не сидировали одновременно
SEED_LOCK_ID = 20261026


def read_seed_file(name: str) -> dict:
    path = get_settings().seed_dir / name
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def seed_products(db: Session) -> None:
    config = get_business_config()
    codes_in_config = set()
    for order, item in enumerate(config.products.products):
        codes_in_config.add(item.code)
        product = db.get(Product, item.code) or Product(code=item.code)
        product.name = item.name
        product.description = item.description
        product.suitable_for = item.suitable_for
        product.purposes = item.purposes
        product.min_amount = item.min_amount
        product.max_amount = item.max_amount
        product.min_term_months = item.min_term_months
        product.max_term_months = item.max_term_months
        product.base_rate = item.base_rate
        product.requires_collateral = item.requires_collateral
        product.decision_days = item.decision_days
        product.required_fields = item.required_fields
        product.sort_order = order
        product.is_active = True
        db.add(product)
    # Продукты, которых больше нет в конфиге, не удаляем (на них могут ссылаться заявки), а выключаем
    for product in db.scalars(select(Product)):
        if product.code not in codes_in_config:
            product.is_active = False
    db.flush()


def seed_companies(db: Session) -> None:
    for item in read_seed_file("companies.json")["companies"]:
        if db.scalar(select(Company).where(Company.inn == item["inn"])):
            continue
        db.add(
            Company(
                inn=item["inn"],
                ogrn=item["ogrn"],
                company_type=item["company_type"],
                name=item["name"],
                okved=item["okved"],
                industry=item["industry"],
                registration_date=date.fromisoformat(item["registration_date"]),
                region=item["region"],
                annual_revenue=Decimal(str(item["annual_revenue"])) if item["annual_revenue"] is not None else None,
                employees_count=item["employees_count"],
            )
        )
    db.flush()


def seed_users(db: Session) -> None:
    for item in read_seed_file("users.json")["users"]:
        if db.scalar(select(User).where(User.login == item["login"])):
            continue
        company_id = None
        if item["company_inn"]:
            company = db.scalar(select(Company).where(Company.inn == item["company_inn"]))
            if company is None:
                raise ValueError(f"users.json: компания с ИНН {item['company_inn']} не найдена в companies.json")
            company_id = company.id
        db.add(
            User(
                login=item["login"],
                # Демо-пароль по правилу «<логин>123» (см. README)
                password_hash=hash_password(f"{item['login']}123"),
                full_name=item["full_name"],
                role=item["role"],
                position=item.get("position"),
                company_id=company_id,
            )
        )
    db.flush()


def seed_applications() -> None:
    """Демо-заявки создаются через те же функции, что и API, поэтому у них настоящие события, проверки и скоринг.

    Ошибка в одной демо-заявке не мешает запуску: это фоновые данные, а не основной сценарий.
    """
    dispatcher = InlineDispatcher()
    application_fields = set(ApplicationCreate.model_fields)
    for item in read_seed_file("applications.json")["applications"]:
        with SessionLocal() as db:
            company = db.scalar(select(Company).where(Company.inn == item["company_inn"]))
            if company is None or db.scalar(select(Application.id).where(Application.company_id == company.id).limit(1)):
                continue  # компании нет или у неё уже есть заявки — значит, seed уже выполнялся
            try:
                author = db.scalar(select(User).where(User.login == item["author_login"]))
                draft = create_draft(db, author, ApplicationCreate(**{key: value for key, value in item.items() if key in application_fields}))
                for step in item["steps"]:
                    if step["actor"] == "client":
                        perform_client_action(db, author, draft.id, step["action"], step.get("comment"), None, dispatcher)
                    else:
                        employee = db.scalar(select(User).where(User.login == step["login"]))
                        perform_employee_action(db, employee, draft.id, step["action"], EmployeeActionRequest(**step["body"]))
                final_status = db.get(Application, draft.id, populate_existing=True).status
                if final_status != item.get("expected_status", final_status):
                    logger.warning(f"Демо-заявка компании {company.name}: статус {final_status}, ожидался {item['expected_status']}")
            except Exception:
                logger.exception("Не удалось создать демо-заявку")


def run_seed() -> None:
    get_business_config()  # проверяем конфиги до любых изменений в БД
    with SessionLocal() as db:
        db.execute(text("SELECT pg_advisory_lock(:id)"), {"id": SEED_LOCK_ID})
        try:
            seed_products(db)
            seed_companies(db)
            seed_users(db)
            db.commit()
        finally:
            db.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": SEED_LOCK_ID})
            db.commit()
    logger.info("Справочники и демо-пользователи загружены")

    with SessionLocal() as db:
        db.execute(text("SELECT pg_advisory_lock(:id)"), {"id": SEED_LOCK_ID})
        try:
            seed_applications()
        finally:
            db.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": SEED_LOCK_ID})
            db.commit()
    logger.info("Демо-заявки загружены")


if __name__ == "__main__":
    setup_logging(get_settings().log_level)
    run_seed()
