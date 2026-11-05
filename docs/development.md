# Разработка в облачной среде

## GitHub Actions

Workflow `.github/workflows/ci.yml` запускается на push, pull request и вручную.
Три независимых задания проверяют:

* Ruff: линтинг и форматирование `src`, `tests`, `scripts`, `server.py`.
* Backend: установку CPU PyTorch, совместимость зависимостей и pytest с JUnit-отчётом.
* Frontend: установку по lockfile, ESLint, генерацию API-клиента, TypeScript и Vite build.

Backend-тесты работают на SQLite с in-memory шиной, stub-провайдерами и отключёнными
скачиваниями Hugging Face. Реальные секреты, PostgreSQL и Telegram для этого задания
не нужны. `tests/e2e` требуют отдельных учётных данных и не запускаются в CI.
JUnit-отчёт сохраняется в artifact `backend-test-results`, в том числе при сбое тестов.
Новый push в ту же ветку отменяет её предыдущий незавершённый запуск.

Локальные эквиваленты:

```bash
python -m pip install -r requirements-dev.txt
ruff check src tests scripts server.py
ruff format --check src tests scripts server.py
pytest tests --ignore=tests/e2e
cd frontend
npm ci --legacy-peer-deps --no-audit --no-fund
npm run lint
npm run build
```

Для локального pytest нужны тестовые `JWT_SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`
и stub-провайдеры. В подготовленной облачной среде эти параметры задаёт временно
`/workspace/companion-setup/run-tests.py` без записи секретов на диск.

Python 3.12, Node.js 24, PostgreSQL 15 с pgvector. Для локальной разработки
используются in-memory шина и `LLM_PROVIDER=stub`, `STT_PROVIDER=stub`,
`TTS_PROVIDER=stub`; интеграционные ключи нужны только при включении реальных API.
Qwen embeddings остаются реальными и прогреваются при старте приложения.

## Установка и проверки

В подготовленной среде доступны:

```bash
bash /workspace/companion-setup/install.sh
bash /workspace/companion-setup/start-db.sh
python3.12 /workspace/companion-setup/run-tests.py
cd /workspace/companion_bot
.venv/bin/ruff check src tests/test_architecture.py tests/modules/memory/test_transactions.py
cd /workspace/companion-setup/frontend
npm run build
```

Установщик использует CPU PyTorch и зафиксированные версии Python-зависимостей
вне checkout; исходные requirements остаются источником прямых зависимостей.
Frontend устанавливается с `npm ci --legacy-peer-deps`: текущие ESLint 10 и
eslint-plugin-react 7 имеют несовместимые peer declarations. Lockfile сохраняется.

В checkout исторически отслеживается часть `node_modules` и Python bytecode.
Чтобы установка не переписывала эти файлы, frontend собирается из копии
`/workspace/companion-setup/frontend`. Редактировать следует исходники в checkout,
затем обновить копию установщиком. Генерация TypeScript-клиента из OpenAPI
выполняется штатным `npm run generate:api`. Правило `/models/` в `.gitignore`
относится только к весам моделей, а не к API-моделям frontend.

Тестовый runner создаёт временные JWT/admin параметры только в процессе,
использует SQLite и не требует реальных секретов. Проверки реальных Telegram
сессий в `tests/e2e` отдельно требуют явной настройки пользователя.

## Запуск приложения

Задать `JWT_SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` в настройках среды.
Не помещать их значения в чат, git или скрипты установки.

```bash
bash /workspace/companion-setup/start-db.sh
cd /workspace/companion_bot
.venv/bin/alembic upgrade head
CREATE_TABLES_ON_STARTUP=False .venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000
```

БД разработки привязана только к loopback, локальная аутентификация — trust;
такая конфигурация предназначена для изолированной среды разработки.
Не применять её к внешней БД или развёртыванию production.

В другом терминале:

```bash
cd /workspace/companion-setup/frontend
npm run dev -- --host 127.0.0.1
```

Готовность backend проверяется ответом `GET /health`, затем логином через
`POST /api/v1/public/auth/login` с JSON `identifier` и `password` из настроек
и чтением `/api/v1/public/users/` с возвращённым Bearer-токеном. Токен и пароль
не выводить в лог. Проверка только открытого порта не подтверждает готовность.

Первый запуск скачивает `Qwen/Qwen3-Embedding-0.6B`. Прокси должен разрешать
`huggingface.co`, `*.huggingface.co`, `*.xethub.hf.co`. На момент подготовки среды
проверка старта остановилась на `403 Forbidden` сетевой политики при прогреве Qwen;
изменения доменов сохранены в черновике, но ещё требуют применения пользователем.
После применения повторить запуск и функциональные запросы. TLS-проверку не отключать.

Снимок сохраняет зависимости и файлы, но не работающие процессы. PostgreSQL,
uvicorn и Vite нужно запускать снова в новой задаче. Использовать имеющийся checkout:
облачная задача уже изолирована, отдельный git worktree не нужен.
