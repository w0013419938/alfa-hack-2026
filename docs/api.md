# API

Базовый адрес API `http://localhost:8000/api/v1`. Через интерфейс тот же API доступен по `http://localhost:3000/api/v1`. Документация открывается в Swagger UI (http://localhost:8000/docs) и ReDoc (http://localhost:8000/redoc), схема лежит в [`docs/openapi.json`](openapi.json), коллекции запросов в [`docs/requests/`](requests/).

Схему нужно перевыгрузить после изменений в API:

```bash
docker compose run --rm -v "$PWD/docs:/docs" backend python -m scripts.export_openapi /docs/openapi.json
```

## Авторизация

`POST /auth/login` с телом `{"login": "...", "password": "..."}` возвращает `access_token`. Это JWT, он живёт 60 минут и передаётся в заголовке `Authorization: Bearer <access_token>`. Ролей две: `client` видит только свою компанию, `employee` работает в бэкофисе. После 5 неудачных попыток входа за минуту вход отвечает `429`.

## Формат ошибок

Любая ошибка приходит в таком виде:

```json
{"error": {"code": "transition_not_allowed", "message": "Действие «Принять предложение» сейчас недоступно: заявка в статусе «Черновик».", "details": {"status": "DRAFT", "action": "accept_offer"}}}
```

| HTTP | Когда | Примеры `code` |
|---|---|---|
| 400 | Запрос корректен по форме, но не по смыслу | `amount_out_of_range`, `unknown_product`, `file_type_not_allowed`, `comment_required` |
| 401 | Нет токена, токен неверный или истёк | `unauthorized`, `invalid_credentials` |
| 403 | Не та роль | `forbidden` |
| 404 | Не найдено (в том числе чужая заявка) | `not_found`, `unknown_action` |
| 409 | Действие сейчас недоступно | `transition_not_allowed`, `precondition_failed`, `version_conflict`, `not_editable` |
| 422 | Ошибка формата входных данных | `validation_error`, в `details` список `{field, message}` |
| 429 | Слишком много попыток входа | `too_many_requests` |

Текст в `message` всегда на русском, его можно показывать пользователю как есть.

## Эндпоинты

### Служебное и справочники (без входа)

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/health` | Процесс жив |
| GET | `/ready` | Доступны БД и mock-external (иначе 503) |
| GET | `/products` | Продукты: описание, «для чего подходит», лимиты, `rate_text` |
| POST | `/products/recommend` | Подбор продукта: `purpose_code`, `amount`, `term_months`, `urgency` (asap/week/month), `has_collateral` → список с `suitable`, `reasons`, `warnings` |
| GET | `/dictionaries/purposes` | Цели кредита |
| GET | `/dictionaries/document-kinds` | Виды документов |
| GET | `/calculator?product=&amount=&term=&payment_type=` | Платёж по базовой ставке, общая сумма, переплата и график по месяцам. `payment_type`: `annuity` (одинаковый платёж, по умолчанию) или `differentiated` (платёж уменьшается) |

### Клиент (`role = client`)

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/auth/me` | Текущий пользователь и его компания |
| GET | `/company` | Моя компания |
| GET | `/applications?page=&page_size=` | Мои заявки (пагинация) |
| POST | `/applications` | Создать черновик (обязателен только `product_code`) |
| GET | `/applications/{id}` | Заявка |
| PATCH | `/applications/{id}` | Изменить анкету (в статусах `DRAFT` и `NEEDS_INFO`); можно передать `version` |
| POST | `/applications/{id}/actions/{action}` | `submit`, `cancel`, `provide_info`, `accept_offer`, `decline_offer`, `sign`; тело (необязательно): `{"comment", "version"}` |
| GET | `/applications/{id}/documents` | Документы заявки |
| POST | `/applications/{id}/documents` | Загрузка: multipart `kind` + `file` (PDF/JPG/PNG до 10 МБ) |
| GET | `/applications/{id}/documents/{doc_id}/download` | Скачать документ |
| GET | `/applications/{id}/contract` | Договор в HTML: проект или подписанный |
| GET | `/feed` | Персональная лента подсказок с `reason` |

### Сотрудник банка (`role = employee`)

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/backoffice/applications?status=&product=&grade=&page=&page_size=` | Очередь; `status` можно передать несколько раз |
| GET | `/backoffice/applications/{id}` | Карточка: анкета, компания, проверки, скоринг с вкладом факторов, итог авторешения, `suggested_offer`, история с payload, документы |
| POST | `/backoffice/applications/{id}/actions/{action}` | `approve`, `counter_offer`, `request_info`, `reject` (только из `MANUAL_REVIEW`, `comment` обязателен) |
| GET | `/backoffice/applications/{id}/documents/{doc_id}/download` | Скачать документ |
| GET | `/backoffice/stats` | Заявки по статусам, доля автоодобрений, среднее время обработки |

Тело действия сотрудника:

| Действие | Поля |
|---|---|
| `approve` | `comment`; по желанию `amount`, `term_months`, `rate` (если их нет, берутся из `suggested_offer`) |
| `counter_offer` | `comment`, `amount`, `term_months`; по желанию `rate` |
| `request_info` | `comment`; по желанию `requested_fields` (коды полей анкеты), `requested_documents` (коды видов документов) |
| `reject` | `comment`, его клиент увидит как причину отказа |

## Заявка в ответе API

Всё, что нужно экрану заявки, приходит в ответе, и фронту ничего не нужно вычислять. Пример в сокращении:

```json
{
  "id": "6da91157-32b2-4d6d-89f6-b8ade1ff5825",
  "number": 1009,
  "status": "OFFER_SENT",
  "status_label": "Есть предложение",
  "status_description": "Банк готов выдать кредит. Посмотрите условия и решите, принимаете ли вы их.",
  "is_final": false,
  "product": {"code": "working_capital", "name": "Оборотный кредит"},
  "amount": 1500000.0, "term_months": 24, "purpose_code": "working_capital", "purpose_label": "Пополнение оборотных средств",
  "monthly_revenue": 800000.0, "monthly_expenses": 550000.0, "current_loan_payments": 0.0,
  "version": 7,
  "available_actions": [
    {"code": "accept_offer", "label": "Принять предложение", "enabled": true, "disabled_reason": null, "requires_comment": false, "confirm_text": null},
    {"code": "decline_offer", "label": "Отказаться от предложения", "enabled": true, "disabled_reason": null, "requires_comment": false,
     "confirm_text": "Отказаться от предложения? Это действие нельзя отменить."}
  ],
  "progress": [
    {"code": "submitted", "label": "Подача заявки", "state": "done", "state_label": "Готово"},
    {"code": "decision", "label": "Решение банка", "state": "action", "state_label": "Ждём вас"},
    {"code": "signing", "label": "Подписание", "state": "upcoming", "state_label": "Впереди"}
  ],
  "timeline": [
    {"at": "2026-10-23T11:32:12Z", "action": "create", "title": "Заявка создана", "status": "DRAFT", "status_label": "Черновик", "actor": "Вы", "comment": null},
    {"at": "2026-10-23T11:32:17Z", "action": "auto_approve", "title": "Банк одобрил заявку", "status": "OFFER_SENT", "status_label": "Есть предложение",
     "actor": "Система", "comment": "Условия: 1 500 000 ₽ на 24 месяца под 21% годовых."}
  ],
  "info_request": null,
  "offer": {"offer_type": "as_requested", "offer_type_label": "На запрошенных условиях", "amount": 1500000.0, "term_months": 24,
            "rate": 21.0, "monthly_payment": 77078.48, "total_payment": 1849883.52, "overpayment": 349883.52,
            "valid_until": "2026-11-22T11:32:17Z", "status": "active", "status_label": "Действует"},
  "documents_count": 0
}
```

В `available_actions` лежат кнопки для текущего пользователя. Кнопку с `enabled: false` нужно показать неактивной и вывести рядом `disabled_reason`. Если есть `confirm_text`, перед действием показывается подтверждение. Коды `edit` и `upload_document` означают, что можно открыть форму анкеты (`PATCH`) и загрузку файлов.

В `progress` семь этапов заявки по порядку. Состояние этапа: `done` (пройден), `current` (банк работает), `action` (ждём клиента), `stopped` (процесс остановился здесь) или `upcoming` (впереди). Какой статус к какому этапу относится, решает бэкенд.

`timeline` содержит историю для экрана заявки. В `comment` банк пишет пояснения: причину отказа, условия, что исправить. Поле `info_request` заполнено в статусе `NEEDS_INFO`: в `fields` перечислено, что исправить, в `documents` какие документы загрузить и загружены ли они.

`version` стоит передавать в `PATCH` и в действиях. Тогда чужие изменения не перезапишутся: при устаревшей версии придёт 409.

## Типовой сценарий запросов

```text
POST /auth/login                                    → токен
GET  /products, POST /products/recommend            → выбор продукта
GET  /calculator?product=...&amount=...&term=...&payment_type=...    → предварительный платёж и график
POST /applications                                  → черновик (DRAFT)
PATCH /applications/{id}                            → правки анкеты
POST /applications/{id}/actions/submit              → SUBMITTED, дальше система
GET  /applications/{id}  (опрос раз в 3 секунды)  → VALIDATION → CHECKS → SCORING → итог
  OFFER_SENT    → POST .../actions/accept_offer → POST .../actions/sign → (система) ISSUED
  NEEDS_INFO    → PATCH / POST .../documents → POST .../actions/provide_info → снова система
  MANUAL_REVIEW → ждём решения сотрудника (POST /backoffice/applications/{id}/actions/...)
  REJECTED      → причина в timeline
```

Статус опрашивается, потому что так проще. В продакшене его можно отдавать через WebSocket или SSE.
