# Умный кредитный кабинет предпринимателя

Прототип цифрового кредитного конвейера для малого и микробизнеса (хакатон Альфа-Банка).

- **Клиент-предприниматель** подбирает продукт, считает платёж, подаёт заявку, видит понятный статус и следующий шаг,
  отвечает на запрос уточнений, принимает предложение и «подписывает» договор.
- **Сотрудник банка** видит очередь заявок, результаты проверок и скоринга с объяснением каждого фактора и принимает
  решение по пограничным случаям.
- **Система** проверяет анкету, запрашивает госреестр и кредитную историю (локальные моки), считает скоринг,
  принимает кредитное решение и формирует предложение — автоматически, за несколько секунд.

Сейчас готовы бэкенд и инфраструктура; фронтенд будет отдельной задачей (API уже отдаёт всё для отображения).

## Архитектура кратко

```
docker compose
├── db             PostgreSQL 16 (volume db_data)
├── mock-external  моки ЕГРЮЛ/ЕГРИП и БКИ с режимами сбоя         :8001
└── backend        FastAPI: API, машина состояний, пайплайн         :8000
                   миграции и демо-данные применяются при старте
```

Подробно: [docs/architecture.md](docs/architecture.md) · статусы: [docs/state-diagram.md](docs/state-diagram.md) ·
модель данных: [docs/data-model.md](docs/data-model.md) · API: [docs/api.md](docs/api.md) ·
допущения: [docs/assumptions.md](docs/assumptions.md).

## Требования

- Docker с Docker Compose v2 (Docker Desktop 4.x или Docker Engine 24+). Больше ничего ставить не нужно.
- Свободные порты 8000 и 8001 (можно поменять: `BACKEND_PORT`, `MOCK_EXTERNAL_PORT` в `.env`).
- Около 2 ГБ свободной памяти, интернет только для первой сборки образов.

## Запуск

```bash
docker compose up --build
```

Готово, когда в логах появится `Uvicorn running on http://0.0.0.0:8000` (первая сборка — 2–4 минуты).
Миграции и демо-данные применяются автоматически; повторный запуск ничего не дублирует.

- Swagger UI: http://localhost:8000/docs (страница подгружает оформление с CDN, поэтому браузеру нужен интернет; сам API работает без него, схема — в `docs/openapi.json`)
- Проверка готовности: http://localhost:8000/api/v1/ready

Начать с чистой базы:

```bash
docker compose down -v && docker compose up --build
```

## Переменные окружения

Все настройки — переменные окружения с безопасными для демо значениями по умолчанию прямо в `docker-compose.yml`,
поэтому файл `.env` не нужен. Чтобы что-то поменять: `cp .env.example .env` и отредактировать.

| Переменная | По умолчанию | Что задаёт |
|---|---|---|
| `JWT_SECRET` | демо-значение | Секрет подписи токенов. Обязательно сменить вне демо (при `APP_ENV=production` демо-секрет запрещён) |
| `JWT_EXPIRE_MINUTES` | 60 | Срок жизни токена |
| `PIPELINE_STEP_DELAY_SECONDS` | 1.5 | Пауза между шагами обработки, чтобы на демо было видно смену статусов (0 — без пауз) |
| `EXTERNAL_TIMEOUT_SECONDS` / `EXTERNAL_MAX_ATTEMPTS` / `EXTERNAL_BACKOFF_SECONDS` | 2 / 3 / 0.5 | Таймаут, попытки и пауза при запросах к внешним сервисам |
| `MOCK_TIMEOUT_SLEEP_SECONDS` | 10 | Сколько «зависает» мок в режиме сбоя `timeout` |
| `LOGIN_RATE_LIMIT_ATTEMPTS` / `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | 5 / 60 | Ограничение неудачных попыток входа |
| `MAX_UPLOAD_MB` / `MAX_DOCUMENTS_PER_APPLICATION` / `ALLOWED_UPLOAD_EXTENSIONS` | 10 / 20 / pdf,jpg,jpeg,png | Ограничения загрузки документов |
| `PIPELINE_WATCHDOG_INTERVAL_SECONDS` / `PIPELINE_STUCK_AFTER_SECONDS` | 60 / 120 | Сторож: как часто искать застрявшие в обработке заявки и когда считать их застрявшими |
| `CORS_ORIGINS` | http://localhost:5173 | Адреса фронтенда |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | credit_cabinet / credit / credit | База данных |
| `BACKEND_PORT` / `MOCK_EXTERNAL_PORT` | 8000 / 8001 | Порты на хосте |

Полный список с пояснениями — в [.env.example](.env.example).

## Тестовые учётки

Пароль каждой учётки — `<логин>123`.

| Логин | Пароль | Компания | Что демонстрирует |
|---|---|---|---|
| `employee` | `employee123` | — (сотрудник банка) | Очередь заявок, карточка со скорингом, ручные решения, статистика |
| `client_good` | `client_good123` | ООО «Северный ветер» | Автоодобрение на запрошенных условиях → принятие → подписание → выдача |
| `client_medium` | `client_medium123` | ООО «Пекарня Каравай» | Высокая долговая нагрузка → встречное предложение |
| `client_border` | `client_border123` | ИП Сидоров П. А. | Пограничный грейд → ручное рассмотрение сотрудником |
| `client_bad` | `client_bad123` | ООО «Ромашка-Строй» | Компания в ликвидации и текущая просрочка → отказ с причиной |
| `client_info` | `client_info123` | ИП Петрова М. И. | Нет выручки по отчётности → запрос выписки → после загрузки предложение |
| `client_timeout` | `client_timeout123` | ООО «ТехноСервис» | БКИ не отвечает (таймаут, ретраи) → ручное рассмотрение |
| `demo1` … `demo8` | `demo1123` … | фоновые компании | Демо-история: 8 заявок в разных статусах, чтобы очередь сотрудника не была пустой |

## Как проверить (5 минут)

1. Откройте http://localhost:8000/docs.
2. `POST /api/v1/auth/login` → **Try it out** → `{"login": "client_good", "password": "client_good123"}` → **Execute**.
   Скопируйте `access_token`, нажмите **Authorize** вверху справа, вставьте токен.
3. `POST /api/v1/applications` с телом:
   ```json
   {"product_code": "working_capital", "amount": 1500000, "term_months": 24, "purpose_code": "working_capital",
    "monthly_revenue": 800000, "monthly_expenses": 550000, "current_loan_payments": 0}
   ```
   Скопируйте `id` из ответа. Статус — «Черновик», в `available_actions` есть «Отправить заявку».
4. `POST /api/v1/applications/{id}/actions/submit` → «Отправлена».
5. Повторяйте `GET /api/v1/applications/{id}`: статус проходит «Проверяем данные» → «Запрашиваем сведения» →
   «Оцениваем заявку» → **«Есть предложение»**. В `timeline` — история с пояснениями, в `offer` — условия и платёж.
6. `POST .../actions/accept_offer`, затем `POST .../actions/sign` → через пару секунд **«Кредит выдан»**.
7. Повторите шаги 2–5 с другими учётками из таблицы — исход будет другим при той же анкете:
   встречное предложение, ручное рассмотрение, отказ, запрос уточнений, сбой БКИ.
8. Войдите как `employee`: `GET /api/v1/backoffice/applications?status=MANUAL_REVIEW` — очередь,
   `GET /api/v1/backoffice/applications/{id}` — карточка со скорингом, `POST .../actions/approve` с `{"comment": "Одобряем"}`.

Все сценарии с ожидаемыми результатами: **[docs/test-scenarios.md](docs/test-scenarios.md)**.
Готовые коллекции запросов: Postman — [docs/requests/credit-cabinet.postman_collection.json](docs/requests/credit-cabinet.postman_collection.json)
(импортируйте и запускайте папки по порядку: токены и id сохраняются сами), VS Code REST Client — [docs/requests/scenarios.http](docs/requests/scenarios.http).

## Тесты

```bash
docker compose run --rm backend uv run pytest
```

167 тестов, около 20 секунд. Юнит-тесты (машина состояний, каждый фактор скоринга, кредитное решение, аннуитет, ИНН,
проверка анкеты, ретраи интеграций) и e2e через API с отдельной тестовой базой (`credit_cabinet_test`) и настоящим
mock-external: сквозные сценарии всех учёток, ручное рассмотрение, права доступа, конкурентные запросы, идемпотентность.
Рабочая база тестами не затрагивается.

## Где лежат данные, которые меняет команда

Код менять не нужно — только эти файлы, затем `docker compose up --build` (для seed-данных — с `down -v`).

| Файл | Что внутри | Кто владелец |
|---|---|---|
| `backend/config/products.yaml` | Продукты: лимиты, ставки, цели, обязательные поля; веса и тексты подбора продукта | участник 2 |
| `backend/config/scoring.yaml` | Факторы скоринга, диапазоны, баллы, объяснения, грейды, отраслевые группы риска | участник 2 |
| `backend/config/decision.yaml` | Стоп-факторы, решения и надбавки по грейдам, допустимая нагрузка, правила встречного предложения и запроса уточнений | участник 2 |
| `backend/config/dictionaries.yaml` | Цели кредита, виды документов, должности | участник 2 |
| `backend/config/labels.yaml` | Все тексты для пользователя: статусы, кнопки, история, причины решений | участник 1 |
| `backend/config/contract_template.html` | Шаблон договора | участник 1 |
| `backend/config/feed.yaml` | Правила ленты подсказок | участник 3 |
| `backend/seed/companies.json`, `users.json` | Демо-компании и пользователи | участник 3 |
| `backend/seed/external_mocks.json` | Ответы моков ЕГРЮЛ и БКИ по ИНН, режимы сбоя | участник 3 |
| `backend/seed/applications.json` | Демо-история заявок для очереди сотрудника | участник 3 |
| `backend/seed/feed_items.json` | Подсказки и новости для ленты | участник 3 |

Места, где ждём данные коллег, помечены `TODO(участник N)`. Конфиги проверяются при старте: если в них ошибка,
бэкенд не запустится и напишет в логе, какое поле неверно.

## Для фронтенда

- Базовый URL: `http://localhost:8000/api/v1`, CORS уже открыт для `http://localhost:5173`.
- Авторизация: `POST /auth/login` → `Authorization: Bearer <access_token>`; `GET /auth/me` — кто вошёл и какая роль.
- Схема: Swagger http://localhost:8000/docs и файл [docs/openapi.json](docs/openapi.json) (можно генерировать типы).
- Экран заявки строится из полей ответа: `status_label`, `status_description`, `available_actions` (кнопки, их подписи,
  активность и текст подтверждения), `timeline`, `info_request`, `offer`. Подробно — [docs/api.md](docs/api.md).
- Обновление статуса после отправки — опрос `GET /applications/{id}` раз в 1–2 секунды, пока статус автоматический.

## Структура репозитория

```
docker-compose.yml, .env.example     запуск
backend/                             API (FastAPI), миграции, конфиги и seed команды, тесты
  app/api | services | domain | integrations | models | schemas | core
  config/  seed/  alembic/  tests/
mock-external/                       моки ЕГРЮЛ/ЕГРИП и БКИ
frontend/                            будет позже
docs/                                архитектура, API, сценарии, допущения, коллекции запросов
```

Сторонние библиотеки, образы и смоделированные интеграции — [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
