# Сторонние компоненты

Все компоненты — свободные, без платных подписок и внешних сетевых сервисов. Версии зафиксированы в
`backend/uv.lock`, `mock-external/uv.lock` и тегах образов в Dockerfile/`docker-compose.yml`.

## Образы Docker

| Образ | Версия | Лицензия | Где используется |
|---|---|---|---|
| `postgres` | 16.15-alpine | PostgreSQL License | сервис `db` |
| `python` | 3.12.15-slim (Debian) | PSF License (Python), лицензии пакетов Debian | базовый образ `backend` и `mock-external` |
| `ghcr.io/astral-sh/uv` | 0.12.21 | MIT / Apache-2.0 | установка зависимостей по lock-файлу при сборке |
| `node` | 22.23.4-alpine | MIT (Node.js) | сборка фронтенда |
| `nginx` | 1.28.0-alpine | BSD-2-Clause | раздача фронтенда и прокси `/api` |
| `mcr.microsoft.com/playwright` | v1.64.1-noble | Apache-2.0 | E2E-тесты интерфейса (только профиль `e2e`) |

## Python-библиотеки бэкенда (`backend/uv.lock`)

| Библиотека | Версия | Лицензия | Назначение |
|---|---|---|---|
| fastapi | 0.161.1 | MIT | веб-фреймворк API |
| starlette | 1.9.0 | BSD-3-Clause | основа FastAPI |
| uvicorn | 0.54.0 | BSD-3-Clause | ASGI-сервер |
| pydantic | 2.14.1 | MIT | валидация данных, схемы API, проверка конфигов |
| pydantic-core | 2.50.1 | MIT | ядро pydantic |
| pydantic-settings | 2.16.1 | MIT | настройки из переменных окружения |
| SQLAlchemy | 2.1.6 | MIT | ORM |
| alembic | 1.20.1 | MIT | миграции БД |
| Mako | 1.4.3 | MIT | шаблоны миграций alembic |
| MarkupSafe | 3.0.4 | BSD-3-Clause | зависимость Mako |
| psycopg / psycopg-binary | 3.3.6 | LGPL-3.0-only | драйвер PostgreSQL (используется как библиотека без изменений) |
| httpx | 0.28.1 | BSD-3-Clause | HTTP-клиент к внешним сервисам, тестовый клиент |
| httpcore | 1.0.9 | BSD-3-Clause | зависимость httpx |
| h11 | 0.16.0 | MIT | зависимость httpx/uvicorn |
| anyio | 4.15.1 | MIT | зависимость starlette/httpx |
| idna | 3.20 | BSD-3-Clause | зависимость httpx |
| certifi | 2026.10.19 | MPL-2.0 | зависимость httpx |
| PyJWT | 2.15.1 | MIT | JWT-токены |
| bcrypt | 5.0.0 | Apache-2.0 | хеширование паролей |
| python-multipart | 0.0.32 | Apache-2.0 | загрузка файлов |
| PyYAML | 6.0.3 | MIT | чтение конфигов |
| python-dotenv | 1.2.4 | BSD-3-Clause | зависимость pydantic-settings |
| click | 8.5.0 | BSD-3-Clause | зависимость uvicorn |
| annotated-types | 0.8.0 | MIT | зависимость pydantic |
| annotated-doc | 0.0.5 | MIT | зависимость fastapi |
| typing-extensions | 4.16.0 | PSF-2.0 | зависимость pydantic/SQLAlchemy |
| typing-inspection | 0.4.4 | MIT | зависимость pydantic |
| opentelemetry-api | 1.45.1 | Apache-2.0 | транзитивная зависимость (не используется напрямую) |
| pytest | 9.1.1 | MIT | тесты (dev) |
| pluggy | 1.7.0 | MIT | зависимость pytest (dev) |
| iniconfig | 2.3.1 | MIT | зависимость pytest (dev) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | зависимость pytest (dev) |
| Pygments | 2.21.0 | BSD-2-Clause | зависимость pytest (dev) |

## Пакеты фронтенда (`frontend/package-lock.json`)

| Пакет | Версия | Лицензия | Назначение |
|---|---|---|---|
| react, react-dom | 19.3.1 | MIT | интерфейс |
| react-router-dom | 7.18.4 | MIT | маршруты |
| @tanstack/react-query | 5.104.5 | MIT | запросы, кеш, опрос статуса |
| @mantine/core, @mantine/hooks, @mantine/notifications | 9.7.3 | MIT | компоненты интерфейса |
| @tabler/icons-react | 3.49.0 | MIT | иконки |
| openapi-fetch | 0.17.0 | MIT | типизированный клиент API |
| @fontsource/golos-text | 5.3.0 | OFL-1.1 | шрифт Golos Text (локально, без интернета) |
| vite, @vitejs/plugin-react | 8.3.5 / 6.1.2 | MIT | сборка (dev) |
| typescript | 5.9.3 | Apache-2.0 | типизация (dev) |
| openapi-typescript | 7.13.0 | MIT | генерация типов из `docs/openapi.json` (dev) |
| @playwright/test | 1.64.1 | Apache-2.0 | E2E-тесты (dev) |
| @types/react, @types/react-dom | 19.3.0 | MIT | типы (dev) |

Транзитивные зависимости (по `package-lock.json`): MIT — 94, MPL-2.0 — 12, Apache-2.0 — 6, ISC — 3, BSD-3-Clause — 2,
MIT OR CC0-1.0 — 2, 0BSD — 1, Python-2.0 — 1, OFL-1.1 — 1. Копилефт-лицензий, требующих раскрытия кода, нет.

Визуальный стиль интерфейса взят из собственных макетов команды в Figma; логотипы и фирменные материалы банка не используются.

## Загружаются браузером при открытии документации API

| Компонент | Версия | Лицензия | Откуда |
|---|---|---|---|
| Swagger UI (`swagger-ui-dist`) | 5.17.14 | Apache-2.0 | cdn.jsdelivr.net, страница `/docs` |
| ReDoc | 2.1.5 | MIT | cdn.jsdelivr.net, страница `/redoc` |

## Python-библиотеки mock-external (`mock-external/uv.lock`)

fastapi, starlette, uvicorn, pydantic, pydantic-core, anyio, h11, idna, click, annotated-types, annotated-doc,
typing-extensions, typing-inspection, opentelemetry-api — те же версии и лицензии, что в таблице выше.

## Смоделированные интеграции

В прототипе нет обращений к реальным системам банка или внешним сервисам. Всё ниже — имитация:

| Интеграция | Как смоделирована | Где |
|---|---|---|
| **ЕГРЮЛ / ЕГРИП** (выписка о компании: статус, дата регистрации, ОКВЭД, руководитель) | Локальный сервис `mock-external`, `GET /egrul/{inn}`; данные из `backend/seed/external_mocks.json`, для неизвестного ИНН — детерминированная генерация | `mock-external/app/main.py` |
| **Бюро кредитных историй** (рейтинг, действующие кредиты, платежи, просрочки) | `mock-external`, `GET /bki/report?inn=`; режимы сбоя `timeout`, `error`, `flaky` для демонстрации отказоустойчивости | `mock-external/app/main.py` |
| **ФНС «Прозрачный бизнес»** | Не подключалась: нужные данные (отрасль, выручка) берутся из профиля компании и анкеты | — |
| **Подписание документов** | Подтверждение действием `sign` в интерфейсе; договор формируется по HTML-шаблону и сохраняется с отметкой «подписано (имитация)»; электронной подписи нет | `backend/app/services/contracts.py` |
| **Выдача средств** | Событие `issue` с суммой в истории заявки; реальных платёжных операций нет | `backend/app/services/pipeline.py` |
| **Уведомления** | Нет email/SMS/мессенджеров: всё, что нужно клиенту, — в статусе и истории заявки | — |

Все данные (компании, ИНН, ФИО, кредитные истории) — синтетические и придуманы для демо. ИНН сгенерированы так,
чтобы проходила проверка контрольной суммы; совпадение с реальными организациями случайно, данные к ним вымышлены.
