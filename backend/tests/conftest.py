"""Общая настройка тестов.

Переменные окружения задаются ДО импорта приложения: тесты работают с отдельной базой
(<основная база>_test), без пауз между шагами пайплайна и с коротким таймаутом внешних сервисов.
"""

import os

# Значения задаются жёстко (не setdefault): внутри `docker compose run` уже есть переменные
# рабочего окружения, а тестам нужны свои — без пауз, с коротким таймаутом и отдельной папкой файлов.
os.environ["JWT_SECRET"] = "test-secret-for-pytest-only-123456"
os.environ["PIPELINE_STEP_DELAY_SECONDS"] = "0"
os.environ["EXTERNAL_TIMEOUT_SECONDS"] = "1"
os.environ["EXTERNAL_MAX_ATTEMPTS"] = "3"
os.environ["EXTERNAL_BACKOFF_SECONDS"] = "0.1"
os.environ["LOGIN_RATE_LIMIT_ATTEMPTS"] = "1000"
os.environ["UPLOAD_DIR"] = "/tmp/credit-cabinet-test-uploads"

# База для тестов: та же, что у приложения, но с суффиксом _test
_main_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://credit:credit@localhost:5432/credit_cabinet")
if not os.environ.get("TEST_DATABASE_PREPARED"):
    base, _, db_name = _main_url.rpartition("/")
    os.environ["MAIN_DATABASE_URL"] = _main_url
    os.environ["DATABASE_URL"] = f"{base}/{db_name}_test"
    os.environ["TEST_DATABASE_PREPARED"] = "1"
