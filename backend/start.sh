#!/bin/sh
# Запуск бэкенда в контейнере: миграции и seed применяются автоматически и идемпотентно.
set -e

echo "Применяем миграции базы данных..."
alembic upgrade head

echo "Загружаем справочники и демо-данные (повторный запуск ничего не дублирует)..."
python -m app.seed

echo "Запускаем API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
