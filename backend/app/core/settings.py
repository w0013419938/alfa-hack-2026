"""Настройки приложения. Все значения приходят из переменных окружения (см. .env.example)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Секрет-заглушка из docker-compose.yml. В режиме production с ним запускаться нельзя.
DEV_JWT_SECRET = "dev-only-secret-change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://credit:credit@localhost:5432/credit_cabinet"

    jwt_secret: str = Field(min_length=16)
    jwt_expire_minutes: int = 60

    # Список адресов фронтенда через запятую
    cors_origins: str = "http://localhost:5173"

    # Внешние сервисы (mock-external)
    external_api_url: str = "http://mock-external:8001"
    external_timeout_seconds: float = 2.0
    external_max_attempts: int = 3
    external_backoff_seconds: float = 0.5

    # Пайплайн обработки заявки
    pipeline_step_delay_seconds: float = 1.5
    pipeline_workers: int = 4

    # Загрузка документов
    upload_dir: Path = Path("/data/uploads")
    max_upload_mb: int = 10
    allowed_upload_extensions: str = "pdf,jpg,jpeg,png"

    # Ограничение попыток входа
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 60

    # Где лежат конфиги и seed-данные команды
    config_dir: Path = BACKEND_DIR / "config"
    seed_dir: Path = BACKEND_DIR / "seed"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def allowed_extension_list(self) -> list[str]:
        return ["." + item.strip().lower().lstrip(".") for item in self.allowed_upload_extensions.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.app_env == "production" and settings.jwt_secret == DEV_JWT_SECRET:
        raise RuntimeError("В режиме production нужно задать собственный JWT_SECRET")
    return settings
