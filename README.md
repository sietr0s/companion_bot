# Companion Bot

Для запуска API без Интернета, моделей, Kafka и клиентских интеграций:
`SAFE_MODE=true uvicorn src.main:app --host 127.0.0.1 --port 8000`.
Нужны установленные Python-пакеты и JWT/admin-настройки из `.env`.
Данные сохраняются в отдельной `safe-mode.db`; PostgreSQL не требуется.
Подробнее — [safe mode](docs/development.md#safe-mode).


Модульный монолит: FastAPI, PostgreSQL/pgvector, Telegram и Instagram,
локальные embeddings и событийный пайплайн companion. Шина — in-memory или Kafka.

## Документация

- [Разработка, запуск и Docker](docs/development.md)
- [Архитектура и границы модулей](docs/adr/0001-module-consistency.md)
- [Память диалога](docs/memory.md)
- [Поведенческие решения](docs/behavior.md)
- [Интеграции и поддерживаемые провайдеры](docs/integrations.md)
- [LLM sampling presets](docs/llm-presets.md)
- [Тесты, покрытие и quality/security gates](docs/code-quality.md)

## Быстрый старт

Python 3.12, Node.js 24, PostgreSQL 15 с pgvector. Установить Python-зависимости:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools -c requirements-ci-constraints.txt
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch -c requirements-ci-constraints.txt
python -m pip install -r requirements-dev.txt -c requirements-ci-constraints.txt
cp .env.example .env
```

Заменить `JWT_SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` в локальном `.env`.
Настройки БД задаются через `DB_*`; по умолчанию это
`postgres:postgres@localhost:5432/modular_monolith`. Полный `DATABASE_URL` не является
входной настройкой: приложение собирает URL из компонентов.

```bash
alembic upgrade head
CREATE_TABLES_ON_STARTUP=False uvicorn src.main:app --reload
```

Приложение прогревает `Qwen/Qwen3-Embedding-0.6B` при старте: первый запуск требует
доступа к Hugging Face и места для весов в `models/`. `LLM_PROVIDER=stub` отключает
внешний чат API, но не локальную embedding-модель.

- `GET /health` — готовность HTTP-приложения.
- `/docs` — OpenAPI UI.
- `pytest tests` — unit/integration/property тесты без внешних аккаунтов.

Docker использует отдельный пример `.env.docker.example`; инструкции —
в [development.md](docs/development.md). Не удалять существующие DB volumes
ради смены ревизии: сначала проверить состояние БД и резервную копию.

## Модули

| Модуль | Ответственность | HTTP-префикс |
| --- | --- | --- |
| `auth` | Учётные записи панели, JWT, seed администратора | `/api/v1/public/auth` |
| `users` | Собеседники `(platform, platform_user_id)` | `/api/v1/public/users` |
| `telegram_clients` | Telethon: SMS/2FA/QR, аккаунты, чаты, whitelist, сообщения | `/api/v1/public/telegram` |
| `instagram_clients` | instagrapi: login/2FA/challenge, polling Direct, текст | `/api/v1/public/instagram` |
| `batching` | Накопление входящих в памяти по ключу `(channel, account_id, chat_id)` | — |
| `memory` | История, summary, retrieval и индекс тем | `/api/v1/public/memory` |
| `behavior` | Intake/delivery, состояние активности и настроения | — |
| `llm` | Chat-провайдеры, embeddings и форматирование промптов | — |
| `stt` | faster-whisper или stub | — |
| `tts` | OpenAI-compatible `/audio/speech` или stub | — |
| `orchestrator` | Маршрутизация пайплайна через шину | — |

Internal HTTP API, SMTP/notifications, storage API, отдельный GLiClass classifier
и DB-батчер в текущем приложении отсутствуют. Не добавлять их старые настройки
или зависимости без реализации соответствующей функции.

## Пайплайн

```text
Telegram/Instagram message
  → users upsert + orchestrator
  → STT для Telegram audio без текста
  → batching → memory.process_batch → memory.build_context
  → behavior.decide_intake
      ignore → остановка
      respond → llm.generate_reply → behavior.decide_delivery
          text → отправка в канал
          voice → TTS → Telegram send_voice (при ошибке — текст)
  → memory.update_memory + behavior.note_delivery
```

Обслуживание индекса/summary запускается через `memory.command.maintain` после
сохранения. Все имена топиков определены в `src/core/bus_topics.py`.
Межмодульные данные — `ChatRef`, `Batch`, `Message`, `Topic`, `ConversationContext`;
синхронные AI-порты находятся в `src/domain/ai.py`, связывание — в `src/composition/`.

Обязательные границы модулей, три слоя данных и структура routers/services:
[ADR 0002](docs/adr/0002-module-boundaries-and-layout.md).
