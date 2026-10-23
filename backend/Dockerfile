FROM python:3.12.15-slim

# uv — менеджер зависимостей; ставит ровно те версии, что зафиксированы в uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_FROZEN=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Сначала только зависимости — этот слой кэшируется, пока не меняется uv.lock.
# Dev-зависимости (pytest) ставим тоже, чтобы тесты запускались в этом же образе.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

# Приложение работает не от root
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /data/uploads \
    && chown -R appuser:appuser /data /app
USER appuser

EXPOSE 8000

# start.sh: миграции -> seed -> запуск API
CMD ["sh", "start.sh"]
