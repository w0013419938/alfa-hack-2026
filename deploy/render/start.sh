#!/usr/bin/env bash
# Запуск контейнера на Render: моки, миграции и seed, API, затем nginx на $PORT.
# Если любой из трёх процессов упадёт, контейнер завершится и Render его перезапустит.
set -euo pipefail

PORT="${PORT:-10000}"

# Render выдаёт адрес базы в виде postgres://... или postgresql://...,
# а бэкенду нужен драйвер psycopg 3: postgresql+psycopg://...
: "${DATABASE_URL:?Нужна переменная DATABASE_URL}"
case "$DATABASE_URL" in
  postgres://*)   DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgres://}" ;;
  postgresql://*) DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgresql://}" ;;
esac
export DATABASE_URL
export EXTERNAL_API_URL="${EXTERNAL_API_URL:-http://127.0.0.1:8001}"
export UPLOAD_DIR="${UPLOAD_DIR:-/data/uploads}"
mkdir -p "$UPLOAD_DIR"

echo "Запускаем моки внешних систем..."
MOCK_DATA_PATH=/srv/mock/data/external_mocks.json \
  /opt/mock-venv/bin/uvicorn app.main:app --app-dir /srv/mock \
  --host 127.0.0.1 --port 8001 --no-access-log &

cd /app
echo "Применяем миграции базы данных..."
alembic upgrade head
echo "Загружаем справочники и демо-данные (повторный запуск ничего не дублирует)..."
python -m app.seed

echo "Запускаем API..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log &

sed "s/__PORT__/${PORT}/" /etc/nginx/conf.d/app.conf.template > /etc/nginx/conf.d/app.conf
echo "Запускаем nginx на порту ${PORT}..."
nginx -g 'daemon off;' &

wait -n
echo "Один из процессов завершился, останавливаем контейнер"
exit 1
