"""Пароли (bcrypt) и токены доступа (JWT)."""

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.settings import get_settings

JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID, role: str) -> tuple[str, int]:
    """Возвращает токен и срок его жизни в секундах."""
    settings = get_settings()
    expires_in = settings.jwt_expire_minutes * 60
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    """Бросает jwt.PyJWTError, если токен неверный или истёк."""
    return jwt.decode(token, get_settings().jwt_secret, algorithms=[JWT_ALGORITHM], options={"require": ["sub", "exp"]})
