# Контекст сборки: корень репозитория (см. docker-compose.yml),
# потому что данные моков лежат в backend/seed/external_mocks.json.
FROM python:3.12.15-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_FROZEN=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY mock-external/pyproject.toml mock-external/uv.lock ./
RUN uv sync --frozen --no-install-project

COPY mock-external/app ./app
COPY backend/seed/external_mocks.json ./data/external_mocks.json

USER nobody

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--no-access-log"]
