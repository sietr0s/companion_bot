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
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me
```

Локально БД по умолчанию: `postgres:postgres@localhost:5432/modular_monolith`.

Схема — одна baseline-ревизия `20260906_baseline` (`CREATE_TABLES_ON_STARTUP` по умолчанию `False`):

```bash
alembic upgrade head
```

Alembic берёт URL из `DB_*` / `settings.DATABASE_URL` (не из `sqlite` в `alembic.ini`). В Docker миграции гоняет `scripts/docker-entrypoint.sh` перед uvicorn.

Если в volume уже была старая цепочка `alembic_version`, том нужно сбросить: `docker compose down -v`, затем `docker compose up --build`.

```bash
uvicorn src.main:app --reload
```

- Health: `GET /health`
- OpenAPI: `http://localhost:8000/docs`

Через Docker (app + frontend + Postgres/pgvector, без Kafka):

```bash
docker compose up --build
```

Секреты и пароли БД берутся из `.env.docker`. Чтобы переопределить их, скопируйте `.env.docker.example` в `.env` в корне репозитория.

Веса embedding-моделей лежат в `./models` (volume). После первой загрузки повторный `docker compose up` их не качает.

- API: `http://localhost:8000`
- Admin UI: `http://localhost:3000` (логин: `ADMIN_EMAIL` / `ADMIN_PASSWORD` из `.env.docker`)
- Postgres: `localhost:5432`
- Kafka: `docker compose --profile kafka up --build` и `MESSAGE_BUS=kafka`
- pgAdmin: `docker compose --profile admin up`

## Слои

| Слой | Роль |
|------|------|
| `src/base` | `BaseModel`, `BaseRepository` (SQL/CRUD), `BaseService` (CRUD без SQL), `create_crud_router` |
| `src/core` | конфиг, БД, JWT, контейнер, топики шины |
| `src/bus` | producer/consumer (`in_memory` или `kafka`) |
| `src/modules/*` | изолированные домены |

Правила модуля (канон: `users`; подробно — [ADR 0001](docs/adr/0001-module-consistency.md)):

- SQL только в репозитории. Наследник `BaseRepository` не переопределяет CRUD, если нет новой логики.
- Сервис вызывает репозиторий, без SQLAlchemy-запросов.
- На ORM-модель с админским CRUD — `create_crud_router`. Bus-only с таблицами (`behavior`) HTTP не поднимает.
- Схемы: `schemas/public.py` (HTTP `EntityCreate|Update|Read`), `schemas/events.py` (шина, `BaseEvent`).
- HTTP-роутеры — пакет `routers/` с экспортом `public_router`.
- Толстый интеграционный модуль (`telegram_clients`): `services/` + `adapters/`, не один `service.py`.

```text
src/modules/<module>/
├── models.py
├── repository.py
├── service.py           # или services/
├── dependencies.py
├── exceptions.py
├── handlers.py
├── routers/
│   ├── __init__.py      # public_router
│   └── public.py
└── schemas/
    ├── public.py
    └── events.py
```

## Модули

| Модуль | Что делает | HTTP |
|--------|------------|------|
| `auth` | админы панели: регистрация, логин, JWT | `/api/v1/public/auth` |
| `users` | собеседники `(platform, platform_user_id)`; `notes` — подсказки для LLM | `/api/v1/public/users` |
| `telegram_clients` | Telethon: аккаунты, QR/SMS, чаты, whitelist | `/api/v1/public/telegram` |
| `instagram_clients` | instagrapi: аккаунты Direct, логин/2FA, poll inbox, whitelist | `/api/v1/public/instagram` |
| `batching` | набор входящих в батч (in-memory), ключ `(channel, account_id, chat_id)` | нет HTTP (только шина) |
| `memory` | диалоги, summary, вектор **тем**; conversation — пара аккаунт+чат; см. [docs/memory.md](docs/memory.md) | `/api/v1/public/memory` |
| `behavior` | intake (отвечать/игнор) и delivery (text/voice), состояние жизни | нет HTTP (только шина) |
| `llm` | чат через LangChain (Mistral или OpenAI-compatible, напр. OpenRouter); эмбеддинги локальные | нет HTTP (только шина) |
| `stt` | транскрипция voice/audio (faster-whisper), скачивание через Telegram | нет HTTP (только шина) |
| `tts` | синтез речи: `fish` (Fish Audio `/v1/tts`), OpenRouter `/audio/speech`, или `stub`; исходящий voice через оркестратор | нет HTTP (только шина) |
| `orchestrator` | пайплайн companion | нет HTTP (только шина) |

Маршрутов `/internal/` нет.

## Пайплайн companion

1. Входящее сообщение Telegram → `telegram_clients.event.message.received`
2. `users` upsert-ит собеседника по `sender_id`
3. Orchestrator: текст → `batching.command.add_message`; voice/audio без текста → `stt.command.transcribe`, затем батч с транскриптом
4. Батч готов → memory сохраняет сообщения и сразу отдаёт пайплайн в `build_context`; затем `memory.command.maintain` (кластеризация и summary). На Kafka maintain выполняется в том же consume-цикле. Подробно: [docs/memory.md](docs/memory.md)
5. `behavior` решает intake (`ignore` обрывает пайплайн)
6. LLM генерирует ответ или подавляет его
7. `behavior` решает delivery: `text` → `telegram_clients.command.send_message`; `voice` → typing delay вне handler шины, затем `tts.command.synthesize` → `send_voice` (при ошибке TTS — текст)
8. Факт отправки → `telegram_clients.event.message.sent` → `memory.command.update_memory` и `behavior.command.note_delivery`

Модули не вызывают друг друга напрямую: команды и события идут через шину.

## Топики шины

Имена: `{module}.event.{action}` и `{module}.command.{action}`. Реестр — `src/core/bus_topics.py`.

| Модуль | Команды | События |
|--------|---------|---------|
| auth | — | `user.registered`, `user.logged_in`, `user.deleted` |
| users | — | `created`, `updated` |
| telegram_clients | `send_message`, `send_voice`, `chat_action` | `message.received`, `message.sent`, `account.connected`, `account.disconnected` |
| batching | `add_message` | `batch.ready`, `batch.completed` |
| memory | `process_batch`, `build_context`, `update_memory`, `maintain` | `batch.processed`, `context.built`, `memory.updated` |
| llm | `generate_reply`, `summarize` | `reply.generated`, `reply.suppressed`, `summary.generated` |
| stt | `transcribe` | `transcribed`, `transcribe_failed` |
| tts | `synthesize` | `synthesized`, `synthesize_skipped` |
| behavior | `decide_intake`, `decide_delivery`, `note_delivery` | `intake_decided`, `delivery_decided` |

## Тесты

```bash
pytest tests --ignore=tests/e2e
```

E2E (`tests/e2e`) требуют живой Telegram API и сессии.

## Стек

Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, Telethon, pytest.
