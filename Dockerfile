# Образ для Render: фронт, бэкенд и моки внешних систем в одном контейнере.
# На бесплатном тарифе Render нет docker compose и приватных сервисов, поэтому
# nginx, API и моки запускаются вместе, а снаружи открыт один порт $PORT.
# Для локального запуска по-прежнему используется docker-compose.yml.

# Шаг 1: сборка фронта (версии пакетов строго по package-lock.json)
FROM node:22.23.4-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
RUN npm run build

# Шаг 2: Python, nginx и собранная статика
FROM python:3.12.15-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_FROZEN=1 \
    UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled/default

# Моки ЕГРЮЛ/ЕГРИП и БКИ, отдельное окружение
WORKDIR /srv/mock
COPY mock-external/pyproject.toml mock-external/uv.lock ./
RUN UV_PROJECT_ENVIRONMENT=/opt/mock-venv uv sync --frozen --no-install-project --no-dev
COPY mock-external/app ./app
COPY backend/seed/external_mocks.json ./data/external_mocks.json

# Бэкенд, без dev-зависимостей
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --frozen --no-install-project --no-dev
COPY backend/ .

COPY --from=frontend /app/dist /usr/share/nginx/html
COPY deploy/render/nginx.conf.template /etc/nginx/conf.d/app.conf.template
COPY deploy/render/start.sh /start.sh

ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 10000
CMD ["bash", "/start.sh"]
