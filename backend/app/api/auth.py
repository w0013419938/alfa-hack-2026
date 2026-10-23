"""Вход в систему и информация о текущем пользователе."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.business_config import get_business_config
from app.core.db import get_db
from app.core.errors import TooManyRequestsError, UnauthorizedError
from app.core.rate_limit import LoginRateLimiter
from app.core.security import create_access_token, hash_password, verify_password
from app.core.settings import get_settings
from app.models import User
from app.models.user import ROLE_EMPLOYEE
from app.schemas.auth import CompanyShort, LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Авторизация"])
logger = logging.getLogger(__name__)

_settings = get_settings()
login_limiter = LoginRateLimiter(_settings.login_rate_limit_attempts, _settings.login_rate_limit_window_seconds)

# Хеш-заглушка: проверяем пароль даже для несуществующего логина,
# чтобы по времени ответа нельзя было узнать, какие логины есть в системе
_DUMMY_HASH = hash_password("dummy-password-for-timing")

ROLE_LABELS = {"client": "Клиент", "employee": "Сотрудник банка"}


def user_to_out(user: User) -> UserOut:
    positions = get_business_config().dictionaries.positions
    company = user.company
    return UserOut(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        role=user.role,
        role_label=ROLE_LABELS.get(user.role, user.role),
        position=user.position,
        position_label=positions.get(user.position) if user.position else None,
        company=CompanyShort(id=company.id, name=company.name, inn=company.inn) if company and user.role != ROLE_EMPLOYEE else None,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход по логину и паролю",
    description="Возвращает JWT. Передавайте его в заголовке `Authorization: Bearer <token>`.",
)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    limiter_key = f"{client_ip}:{body.login.lower()}"
    if login_limiter.is_blocked(limiter_key):
        raise TooManyRequestsError("Слишком много неудачных попыток входа. Подождите минуту и попробуйте снова.")

    user = db.scalar(select(User).where(User.login == body.login))
    password_ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not password_ok or not user.is_active:
        login_limiter.register_failure(limiter_key)
        logger.info("Неудачная попытка входа")
        raise UnauthorizedError("Неверный логин или пароль", code="invalid_credentials")

    login_limiter.reset(limiter_key)
    token, expires_in = create_access_token(user.id, user.role)
    logger.info("Успешный вход", extra={"user_id": str(user.id)})
    return TokenResponse(access_token=token, expires_in=expires_in, user=user_to_out(user))


@router.get("/me", response_model=UserOut, summary="Текущий пользователь")
def me(user: User = Depends(get_current_user)):
    return user_to_out(user)
