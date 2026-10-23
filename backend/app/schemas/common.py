"""Общие типы для схем API."""

from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, PlainSerializer

# Деньги храним как Decimal (без ошибок округления), а в JSON отдаём числом — так удобнее фронту
Money = Annotated[Decimal, PlainSerializer(lambda value: float(value), return_type=float, when_used="json")]

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Страница списка."""

    items: list[T]
    total: int
    page: int
    page_size: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list | dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
