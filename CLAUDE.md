# Умный кредитный кабинет предпринимателя

Прототип цифрового кредитного конвейера для малого и микробизнеса (хакатон Альфа-Банка, сдача 26.10.2026). Клиент подаёт заявку на кредит в веб-кабинете, банк обрабатывает её (проверки → скоринг → решение), клиент видит статус и принимает предложение.

Полное ТЗ бэкенда: `TASK_BACKEND.md`. Прогресс работы: `docs/PROGRESS.md`.

## Команды

- Запуск всего: `docker compose up --build`
- Сброс с нуля: `docker compose down -v && docker compose up --build`
- Тесты: `docker compose run --rm backend uv run pytest`
- Новая миграция: `docker compose run --rm backend uv run alembic revision --autogenerate -m "<описание>"`
- Swagger: http://localhost:8000/docs
- Интерфейс: http://localhost:3000
- E2E-тесты интерфейса: `docker compose --profile e2e run --rm e2e`
- Скриншоты для docs: `docker compose --profile e2e run --rm -e SCREENSHOTS=1 e2e npx playwright test --grep @screenshots`
- Типы API для фронта после изменения бэкенда: экспорт `docker compose run --rm -v "$PWD/docs:/docs" backend python -m scripts.export_openapi /docs/openapi.json`, затем `npm run gen:api` в `frontend/` (Node 22, удобно через `docker run node:22.23.4-alpine`)

## Архитектура в двух словах

- `backend/` — FastAPI + PostgreSQL. Логика процесса в `app/domain/`, пайплайн в `app/services/`.
- `mock-external/` — отдельный сервис-мок БКИ и ЕГРЮЛ/ЕГРИП.
- `frontend/` — React + Vite + TypeScript, Mantine, TanStack Query. Тема — `src/theme.ts`, подсказки к терминам — `src/texts/glossary.ts`, типы API — `src/api/schema.d.ts` (генерируются, руками не править).

## Правила проекта

- Смена статуса заявки — только через `app/domain/state_machine.py`, с записью `ApplicationEvent`.
- Фронт ничего не вычисляет сам: API отдаёт `status_label`, `status_description`, `available_actions`, `progress`, `timeline`. Кнопки — только из `available_actions`, соответствие статусов этапам — только из `progress`.
- Продукты, правила скоринга, пороги решений, тексты статусов и демо-данные живут в `backend/config/` и `backend/seed/`. Их владельцы — другие участники команды, поэтому код не должен содержать эти значения захардкоженными.
- Только синтетические данные, только локальные моки, никаких платных API и сетевых сервисов вне docker compose.
- Код читают джуниор-разработчики: простые имена, без лишних абстракций.
- Тексты для пользователя и сообщения об ошибках — на русском, понятные человеку без банковской экспертизы.
- Допущения и упрощения записываются в `docs/assumptions.md`.
