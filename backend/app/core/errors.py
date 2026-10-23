"""Единый формат ошибок API: {"error": {"code", "message", "details"}}.

Сообщения — на русском и понятны человеку без банковской экспертизы.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Базовая ошибка приложения. Бросайте её (или наследников) из любого слоя."""

    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, details: dict | list | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details
        if code:
            self.code = code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class TooManyRequestsError(AppError):
    status_code = 429
    code = "too_many_requests"


def error_body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


# Перевод типовых ошибок валидации Pydantic на русский
VALIDATION_MESSAGES = {
    "missing": "Обязательное поле",
    "greater_than": "Значение должно быть больше {gt}",
    "greater_than_equal": "Значение должно быть не меньше {ge}",
    "less_than": "Значение должно быть меньше {lt}",
    "less_than_equal": "Значение должно быть не больше {le}",
    "string_too_short": "Слишком короткое значение (минимум {min_length} симв.)",
    "string_too_long": "Слишком длинное значение (максимум {max_length} симв.)",
    "int_parsing": "Нужно целое число",
    "int_type": "Нужно целое число",
    "int_from_float": "Нужно целое число",
    "float_parsing": "Нужно число",
    "decimal_parsing": "Нужно число",
    "bool_parsing": "Нужно значение true или false",
    "literal_error": "Недопустимое значение. Допустимо: {expected}",
    "enum": "Недопустимое значение. Допустимо: {expected}",
    "uuid_parsing": "Некорректный идентификатор",
    "json_invalid": "Некорректный JSON в теле запроса",
    "extra_forbidden": "Неизвестное поле",
    "string_pattern_mismatch": "Значение в неверном формате",
    "model_attributes_type": "Некорректный формат данных",
    "dict_type": "Ожидается объект",
    "list_type": "Ожидается список",
}


def translate_validation_errors(errors: list[dict]) -> list[dict]:
    result = []
    for error in errors:
        template = VALIDATION_MESSAGES.get(error.get("type", ""))
        context = error.get("ctx") or {}
        if template:
            # Pydantic перечисляет варианты по-английски: 'a', 'b' or 'c'
            context = {key: str(value).replace(" or ", " или ") for key, value in context.items()}
            try:
                message = template.format(**context)
            except (KeyError, IndexError):
                message = template
        else:
            message = "Некорректное значение"
        # Пропускаем служебную часть пути ("body", "query")
        location = [str(part) for part in error.get("loc", []) if part not in ("body", "query", "path")]
        # Для ошибок всего тела (пустое тело, неверный JSON) поля нет
        field = ".".join(location) if location and error.get("type") != "json_invalid" else None
        result.append({"field": field, "message": message})
    return result


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    def handle_app_error(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error_body(
                "validation_error",
                "Проверьте введённые данные",
                translate_validation_errors(exc.errors()),
            ),
        )

    @app.exception_handler(StaleDataError)
    def handle_stale_data(request: Request, exc: StaleDataError):
        return JSONResponse(
            status_code=409,
            content=error_body("version_conflict", "Заявку только что изменили. Обновите страницу и повторите действие."),
        )

    @app.exception_handler(DataError)
    def handle_data_error(request: Request, exc: DataError):
        # Например, символ NUL (\x00) в тексте: PostgreSQL такие строки не принимает
        return JSONResponse(
            status_code=422,
            content=error_body("invalid_characters", "В данных есть недопустимые символы. Проверьте введённый текст."),
        )

    @app.exception_handler(StarletteHTTPException)
    def handle_http_error(request: Request, exc: StarletteHTTPException):
        messages = {
            401: "Нужно войти в систему",
            403: "Недостаточно прав",
            404: "Страница не найдена",
            405: "Метод не поддерживается",
        }
        message = messages.get(exc.status_code, "Ошибка запроса")
        return JSONResponse(status_code=exc.status_code, content=error_body("http_error", message), headers=exc.headers)

    @app.exception_handler(Exception)
    def handle_unexpected_error(request: Request, exc: Exception):
        # Обычно сюда не доходит: ошибку раньше перехватывает RequestIdMiddleware. Это запасной вариант.
        logger.error("Непредвиденная ошибка", exc_info=exc, extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "Что-то пошло не так. Попробуйте ещё раз чуть позже."),
        )
