# Modular Monolith — Digital Companion

Модульный монолит с event-driven шиной сообщений.

## Быстрый старт

```bash
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.main:app --reload
```

Swagger UI: `http://localhost:8000/docs`

## Модули

| Модуль | Описание |
|--------|----------|
| `auth` | Аутентификация и авторизация (JWT) |
| `users` | Пользователи Telegram |
| `telegram_clients` | Транспорт для Telegram (Telethon) |
| `batching` | Группировка сообщений в батчи |
| `memory` | Память диалогов, контекст, RAG |
| `llm` | Генерация ответов через LLM |
| `orchestrator` | Координация потока сообщений |

## Структура модуля

```text
src/modules/<module_name>/
├── __init__.py           # Публичный API
├── dependencies.py       # DI-фабрики
├── handlers.py           # Обработчики шины
├── routers.py            # HTTP endpoints (опционально)
├── models.py             # SQLAlchemy ORM
├── schemas_api.py        # Pydantic схемы для HTTP
├── schemas_bus.py        # Pydantic схемы для шины
├── service.py            # Бизнес-логика
├── repository.py         # Репозиторий
└── exceptions.py         # Исключения модуля
```

## Архитектура

- **Event-driven**: модули общаются только через шину событий
- **Изоляция**: нет прямых вызовов между модулями
- **Оркестратор**: координирует поток, подписан на все `.out` топики

## Топики шины

| Модуль | `.in` | `.out` |
|--------|-------|--------|
| users | get_or_create, update_last_seen | user_created, user_found |
| telegram_clients | send_message | message_received, message_sent |
| batching | add_message | batch_ready |
| memory | process_batch, build_context, update_memory | batch_processed, context_built, memory_updated |
| llm | generate_reply, summarize, pre_retrieve, post_retrieve | reply_generated, reply_suppressed, summary_generated |
| orchestrator | все `.out` | все `.in` |

## Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Проверки: `ruff`, `mypy`, `pytest`
