# Разработка и запуск

## Требования и зависимости

Python 3.12, Node.js 24, PostgreSQL 15/pgvector. Установка описана в
[README](../README.md). `requirements.txt` содержит runtime-зависимости;
`requirements-dev.txt` добавляет pytest/Hypothesis, SQLite driver и Ruff;
`requirements-quality.txt` — mypy, Radon, Bandit, Vulture и pip-audit.
`requirements-ci-constraints.txt` закрепляет проверенный Linux/Python 3.12 набор.

SQLite используется только в тестах. Kafka, Telethon, instagrapi, chat SDK и
локальные ML-библиотеки относятся к действующим возможностям приложения и
сохраняются, даже если CI заменяет внешние вызовы fake-провайдерами.

## Локально

Скопировать `.env.example` в `.env`, задать обязательные JWT/admin значения и
подключение `DB_*`. Пример использует stub chat/STT/TTS, in-memory bus.
Для реальных интеграций — [integrations.md](integrations.md).

```bash
source .venv/bin/activate
alembic upgrade head
CREATE_TABLES_ON_STARTUP=False uvicorn src.main:app --reload
```

Миграции — основной способ создания схемы. `CREATE_TABLES_ON_STARTUP=True`
по умолчанию оставлен как dev-режим `create_all`, но не обновляет существующую
схему и не заменяет Alembic. Рекомендуемые примеры выставляют `False`.

Frontend:

```bash
cd frontend
npm ci --legacy-peer-deps --no-audit --no-fund
npm run dev -- --host 127.0.0.1
```

Vite проксирует `/api` и `/health` на backend:8000. После изменения backend API:

```bash
python scripts/generate_frontend_openapi.py
cd frontend
npm run generate:api
npm run build
```

Генератор фильтрует HTTP-контракт панели. Не редактировать generated-клиент вручную.

## Docker

```bash
cp .env.docker.example .env
# Задать собственные JWT/admin/DB пароли в .env.
docker compose up --build
```

Compose передаёт настройки через `.env`; отдельный `.env.docker` не требуется.
`docker-entrypoint.sh` выполняет `alembic upgrade head`, затем запускает uvicorn.
Backend image содержит CPU PyTorch и runtime-пакеты; frontend image использует Node 24.
Markdown-промпты входят в image. Тесты, frontend node_modules, отчёты и локальные
`.env` в backend image не копируются.

API: порт 8000; admin UI: 3000; PostgreSQL: 5432.
Профили: `--profile kafka` (Kafka/ZooKeeper/console), `--profile admin` (pgAdmin).
Сессии сохраняются в `sessions/`, веса — в `models/`, БД — в named volume.
Не использовать `docker compose down -v` как обычный шаг обновления: это удаляет данные.

Первый запуск прогревает Qwen и, при выборе faster-whisper, speech model.
Нужны сетевой доступ и место для весов. `stub` chat не заменяет embedding-модель.
За прокси сохранить TLS-проверку; optional BuildKit secret `proxy_ca` позволяет
передать combined CA bundle только на время установки Python-пакетов:

```bash
docker build --secret id=proxy_ca,src=/path/to/combined-ca-bundle.pem -t companion-bot .
```

## Проверки и CI

```bash
python -m pip install -r requirements-dev.txt -r requirements-quality.txt -c requirements-ci-constraints.txt
ruff check src tests scripts
ruff format --check src tests scripts
pytest tests
python scripts/quality_report.py
python scripts/audit_python.py
cd frontend
npm run lint
npm run test:coverage
npm run build
```

Для pytest нужны тестовые `JWT_SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` и
`LLM_PROVIDER=stub`, `STT_PROVIDER=stub`, `TTS_PROVIDER=stub`; они заданы в `ci.yml`.
Тесты не подключаются к рабочим Telegram/Instagram/LLM-сервисам. Подробные команды
покрытия, quality baseline и расположение отчётов — [code-quality.md](code-quality.md).
Реальных внешних E2E сейчас нет: старые заглушки удалены, полезные auth HTTP-сценарии
проверяются в обычных интеграционных тестах.

`CI` проверяет Ruff, backend tests/coverage и frontend lint/tests/build.
`Code quality` проверяет типы, сложность, мёртвый код, дубликаты, безопасность и
сам workflow. Повторные dependency-аудиты и Dependabot выполняются еженедельно
после merge конфигурации в default branch.

## Подготовленная cloud-среда

Основной checkout — `/workspace/companion_bot`; отдельный worktree не нужен.
Проверенный чистый Python env — `/workspace/companion-clean-env`; PostgreSQL запускается вспомогательным
`/workspace/companion-setup/start-db.sh`. Вспомогательные cloud-скрипты не являются
частью проекта: portable-команды выше остаются основным рабочим процессом.

Frontend может собираться в `/workspace/companion-setup/frontend` для изоляции
установки. При редактировании обновлять эту копию; canonical исходники — checkout.
`node_modules`, bytecode, egg-info и отчёты больше не отслеживаются в Git.

Процессы после snapshot нужно запускать заново. Признак готовности — ответ
`GET /health`, затем login через `POST /api/v1/public/auth/login` и авторизованный
`GET /api/v1/public/users/`, без вывода токена/пароля в лог.
Если proxy блокирует прогрев модели, проверить разрешённые HF/CDN destinations
и повторить запуск после применения настроек; один открытый порт не доказывает
готовность приложения.
