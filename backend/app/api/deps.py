"""Общие зависимости эндпоинтов: текущий пользователь и проверка роли."""

import uuid

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models import User
from app.models.user import ROLE_CLIENT, ROLE_EMPLOYEE

bearer_scheme = HTTPBearer(auto_error=False, description="Токен из POST /api/v1/auth/login")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Нужно войти в систему")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise UnauthorizedError("Сессия истекла или недействительна. Войдите заново.") from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Сессия истекла или недействительна. Войдите заново.")
    return user


def get_current_client(user: User = Depends(get_current_user)) -> User:
    if user.role != ROLE_CLIENT or user.company_id is None:
        raise ForbiddenError("Этот раздел доступен только клиентам банка")
    return user


def get_current_employee(user: User = Depends(get_current_user)) -> User:
    if user.role != ROLE_EMPLOYEE:
        raise ForbiddenError("Этот раздел доступен только сотрудникам банка")
    return user
