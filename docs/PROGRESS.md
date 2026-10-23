# Прогресс разработки бэкенда

Если вы продолжаете работу с новым контекстом: прочитайте этот файл и `git log`,
затем продолжайте с первого незавершённого этапа.

## Чек-лист этапов (по разделу «Порядок работы» ТЗ)

- [x] 1. Каркас: структура, Docker Compose (`db`, `mock-external`, `backend`), `/health`, lock-файлы, `.env.example`
- [x] 2. Модели, миграции, seed-загрузчик, авторизация (JWT) и роли
- [x] 3. Машина состояний + `ApplicationEvent` + `available_actions` + тексты из `labels.yaml`
- [x] 4. Клиентские эндпоинты, продукты, подбор продукта, калькулятор
- [x] 5. `mock-external` + клиенты интеграций с ретраями и таймаутами
- [x] 6. Скоринг, кредитное решение, расчёт предложения, пайплайн
- [ ] 7. Бэкофис-эндпоинты и статистика
- [ ] 8. Документы (загрузка) и имитация подписания и выдачи
- [ ] 9. Лента подсказок `/feed`
- [ ] 10. Тесты (юнит + e2e) — зелёные
- [ ] 11. Документация, `openapi.json`, коллекция запросов, `THIRD_PARTY_NOTICES.md`
- [ ] 12. Финальная проверка с нуля (`docker compose down -v && docker compose up --build`) + проверка субагентом-«жюри»

## Ключевые решения (кратко, подробно — в `docs/assumptions.md`)

- Синхронный SQLAlchemy 2.x + psycopg 3: проще для джуниоров, FastAPI запускает sync-эндпоинты в пуле потоков.
- Фоновая обработка — через `PipelineDispatcher` (сейчас пул потоков), позже можно заменить на очередь.
- Пайплайн — набор шагов «по статусу»: каждый шаг смотрит текущий статус и делает один переход.
  Поэтому обработку можно безопасно перезапустить (при старте бэкенд добирает «зависшие» заявки).
- Демо-история заявок для очереди сотрудника создаётся при seed теми же функциями, что и в API.

## Журнал этапов

### Этап 1 — каркас (готово)
- docker-compose: `db` (PostgreSQL 16.15), `mock-external`, `backend`; healthchecks, `restart: unless-stopped`, место под `frontend`.
- Имя compose-проекта задано явно (`name: credit-cabinet`): из кириллического имени папки Compose не может его вывести.
- Порт БД наружу не публикуется (чтобы не конфликтовать с локальным PostgreSQL у жюри).
- Lock-файлы `uv.lock` для backend и mock-external; образы закреплены по версиям.
- `/api/v1/health`, `/api/v1/ready` (проверяет БД и mock-external), JSON-логи с request id.

### Этап 2 — модели, миграции, seed, авторизация (готово)
- Модели всех сущностей ТЗ (`app/models/`), начальная миграция Alembic (autogenerate), UUID-ключи, номер заявки с 1001.
- Оптимистичная блокировка заявки через `version_id_col`.
- Бизнес-конфиги `backend/config/*.yaml` проверяются Pydantic-моделями при загрузке (`app/core/business_config.py`).
- Seed (`python -m app.seed`) идемпотентный, под `pg_advisory_lock`; продукты обновляются из YAML каждый старт.
- JWT (HS256), bcrypt, роли client/employee, rate limit на вход (in-memory). Проверено: 401, 429, повторный старт.

### Этап 3 — машина состояний (готово)
- `app/domain/state_machine.py`: таблица `TRANSITIONS` (из статусов, действие → статус, роли, предусловие, обязательный комментарий).
- `apply_transition()` — SELECT FOR UPDATE + проверки + запись `ApplicationEvent` в одной транзакции; 409 при недопустимом переходе.
- `available_actions()` возвращает кнопки с `enabled`/`disabled_reason` (например, «сначала загрузите документ»).
- `app/services/presenters.py` собирает ответ: `status_label`, `status_description`, `available_actions`, `timeline`, `info_request`, `offer`.
- Тексты — `config/labels.yaml`. Юнит-тесты таблицы переходов зелёные; через API проверяется на этапе 4.

### Этап 4 — клиентские эндпоинты (готово)
- `/company`, `/applications` (список, создание, просмотр, PATCH черновика с `version`), `/applications/{id}/actions/{action}`.
- `/products`, `/products/recommend` (правила и тексты — `products.yaml`), `/dictionaries/purposes`, `/dictionaries/document-kinds`, `/calculator`.
- Документы и договор (`/applications/{id}/documents`, `/contract`) написаны заранее — проверяются на этапе 8.
- Идемпотентность: повтор последнего действия тем же пользователем возвращает текущее состояние (200), а не 409.
- Проверено запросами: 409 при конфликте версий и недопустимом переходе, 404 на чужую заявку, 403 сотруднику в клиентском разделе.

### Этап 5 — mock-external и клиент интеграций (готово)
- `mock-external`: `/egrul/{inn}`, `/bki/report?inn=`; данные из `seed/external_mocks.json`, для неизвестного ИНН — детерминированная генерация.
- Режимы сбоя: `timeout`, `error` (500), `flaky` (каждый нечётный запрос — 503, видно ретраи).
- `app/integrations/external_client.py`: интерфейс + HTTP-реализация; таймаут, ретраи с экспоненциальной паузой, 4xx не повторяются,
  наружу исключения не летят — результат со статусом ok/error/timeout. Request id пробрасывается в мок.
- Юнит-тесты клиента на `httpx.MockTransport`; проверено и вживую из контейнера бэкенда.

### Этап 6 — скоринг, решение, предложение, пайплайн (готово)
- `domain/validation.py` (VALIDATION), `domain/scoring.py` (факторы → баллы → грейд), `domain/decision.py`
  (стоп-факторы → ошибки интеграций → нехватка данных → грейд → встречное предложение), `domain/payments.py` (аннуитет).
- `services/pipeline.py`: шаги по статусу, по одному переходу в транзакции; сбой шага → `technical_error` → MANUAL_REVIEW;
  при старте бэкенд возобновляет прерванные заявки (проверено перезапуском контейнера посреди обработки).
- Все 6 демо-учёток дают ожидаемый исход через API: good → OFFER_SENT (as_requested), medium → OFFER_SENT (counter_offer),
  border → MANUAL_REVIEW, bad → REJECTED, info → NEEDS_INFO → (выписка + provide_info) → OFFER_SENT, timeout → MANUAL_REVIEW.
- Цепочка accept_offer → sign → ISSUED, договор HTML сохраняется документом; загрузка файлов проверяет тип по сигнатуре.

## Известные проблемы

(пока нет)

## Идеи на потом

(пока нет)
