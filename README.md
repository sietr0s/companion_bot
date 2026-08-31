# Companion Bot

Модульный монолит: FastAPI, PostgreSQL, event-driven шина (in-memory или Kafka).

## Быстрый старт

```bash
python3.12 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Обязательные переменные окружения:

```env
JWT_SECRET_KEY=change-me
INTERNAL_SERVICE_KEY=change-me
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me
```

Локально БД по умолчанию: `postgres:postgres@localhost:5432/modular_monolith`.

```bash
uvicorn src.main:app --reload
```

- Health: `GET /health`
- OpenAPI: `http://localhost:8000/docs`

Через Docker: `docker compose up --build`.

## Слои

| Слой | Роль |
|------|------|
| `src/base` | `BaseModel`, `BaseRepository` (SQL/CRUD), `BaseService` (CRUD без SQL), `create_crud_router` |
| `src/core` | конфиг, БД, JWT, контейнер, топики шины |
| `src/bus` | producer/consumer (`in_memory` или `kafka`) |
| `src/modules/*` | изолированные домены |

Правила модуля:

- SQL только в репозитории. Наследник `BaseRepository` не переопределяет CRUD, если нет новой логики.
- Сервис вызывает репозиторий, без SQLAlchemy-запросов.
- На каждую ORM-модель — HTTP CRUD через `create_crud_router`.
- Схемы лежат в `schemas/`: `public.py` (HTTP), `events.py` (шина), при необходимости `internal.py`.

```text
src/modules/<module>/
├── models.py
├── repository.py
├── service.py
├── dependencies.py
├── handlers.py          # подписки на шину (если нужны)
├── routers.py           # или routers/
└── schemas/
    ├── public.py
    └── events.py
```

## Модули

| Модуль | Что делает | HTTP |
|--------|------------|------|
| `auth` | админы панели: регистрация, логин, JWT | `/api/v1/public/auth` |
| `users` | собеседники Telegram (не связан с auth); `notes` — подсказки для LLM | `/api/v1/public/users` |
| `telegram_clients` | Telethon: аккаунты, QR/SMS, чаты, whitelist | `/api/v1/public/telegram` |
| `batching` | набор входящих сообщений в батч | `/api/v1/public/batches` |
| `memory` | диалоги, сообщения, summary; vector retrieve in-process (LLM embed/pre/post/summarize) | `/memory` |
| `llm` | заглушка генерации ответа | нет HTTP (только шина) |
| `orchestrator` | пайплайн companion | нет HTTP (только шина) |

Маршрутов `/internal/` нет.

## Пайплайн companion

1. Входящее сообщение Telegram → `telegram_clients.event.message.received`
2. `users` upsert-ит собеседника по `sender_id`
3. Orchestrator → `batching.command.add_message`
4. Батч готов → memory: `process_batch` / `update_memory` сохраняют сообщения, индексируют батч (document embed → `VectorRecord`) и при пороге 50 вызывают summarize; `build_context` делает pre → vector search → post и собирает Summary / Retrieved / last N
5. LLM генерирует ответ или подавляет его
6. Orchestrator → `telegram_clients.command.send_message`
7. Факт отправки → `telegram_clients.event.message.sent`

Модули не вызывают друг друга напрямую: команды и события идут через шину.

## Топики шины

Имена: `{module}.event.{action}` и `{module}.command.{action}`. Реестр — `src/core/bus_topics.py`.

| Модуль | Команды | События |
|--------|---------|---------|
| auth | — | `user.registered`, `user.logged_in`, `user.deleted` |
| users | — | `created`, `updated` |
| telegram_clients | `send_message` | `message.received`, `message.sent`, `account.connected`, `account.disconnected` |
| batching | `add_message` | `batch.ready`, `batch.completed` |
| memory | `process_batch`, `build_context`, `update_memory` | `batch.processed`, `context.built`, `memory.updated` |
| llm | `generate_reply`, `summarize` | `reply.generated`, `reply.suppressed`, `summary.generated` |

Необработанные сообщения попадают в `bus.dlq`.

## Тесты

```bash
pytest tests --ignore=tests/e2e
```

E2E (`tests/e2e`) требуют живой Telegram API и сессии.

## Стек

Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, Telethon, pytest.
