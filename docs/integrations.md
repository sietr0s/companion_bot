# Поддерживаемые интеграции

## Telegram

`telegram_clients` использует Telethon, а не Bot API. API приложения поддерживает
SMS-код, облачный пароль 2FA и QR-авторизацию. Нужны `TG_API_ID` / `TG_API_HASH`;
файлы сессий хранятся в `TG_SESSION_DIR`. API-аккаунты и whitelist управляются
через `/api/v1/public/telegram`; полная схема запросов — в `/docs`.

Входящее сообщение публикуется как `telegram_clients.event.message.received`.
Медиа передаются в виде Telegram ID и типа, без загрузки в storage API. Голосовые
сообщения для STT скачиваются по запросу через текущий Telethon-клиент.
SMS-коды, их hashes и пароли не должны попадать в логи.

## Instagram

`instagram_clients` использует синхронный instagrapi через thread pool.
Поддерживаются login/2FA/challenge, сохранение сессии в JSON и polling Direct inbox.
Вызовы сериализуются для одного аккаунта. Пароль не сохраняется приложением.

Настройки: `INSTAGRAM_POLL_INTERVAL_S` (20 секунд) и `INSTAGRAM_SESSION_DIR`
(`sessions/instagram`). API: `/api/v1/public/instagram`.
Поддерживается текстовый companion; voice delivery для Instagram блокируется.
Posts/stories, MQTT и автоматическое принятие pending requests не реализованы.

## Chat и embeddings

| `LLM_PROVIDER` | Настройки |
| --- | --- |
| `stub` | Без внешнего API; предназначен для разработки и тестов |
| `mistral` | `MISTRAL_API_KEY`, `MISTRAL_MODEL` |
| `google` | `GOOGLE_API_KEY`, `GOOGLE_MODEL` |
| `openrouter` | `LLM_API_KEY`, `LLM_MODEL`; стандартный OpenRouter endpoint |
| `openai` | `LLM_API_KEY`, `LLM_MODEL`; стандартный OpenAI endpoint |
| `openai_compat` | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` |

Presets `reply`, `rag`, `extract` описаны в [llm-presets.md](llm-presets.md).
Локальная модель `EMBEDDING_MODEL` по умолчанию — `Qwen/Qwen3-Embedding-0.6B`;
изменение её размерности требует согласования с `EMBEDDING_DIM` и схемой векторов.
`MODEL_CACHE_DIR` используется для HF / sentence-transformers / torch cache.
Embeddings прогреваются при запуске даже при `LLM_PROVIDER=stub`.

LangSmith включается отдельно через `LANGSMITH_TRACING` и `LANGSMITH_API_KEY`.
Для нормальной работы приложения tracing не обязателен.

## STT / TTS

`STT_PROVIDER=stub` не обращается к внешним сервисам.
`STT_PROVIDER=faster_whisper` (также `whisper`) использует faster-whisper,
`WHISPER_MODEL` и `WHISPER_DEVICE`. Первая загрузка весов требует сети.

`TTS_PROVIDER=stub` приводит к текстовому fallback. `openrouter`, `openai` и
`openai_compat` используют адаптер OpenAI-compatible `/audio/speech`:
`LLM_API_KEY`, `LLM_BASE_URL`, `TTS_MODEL`, `TTS_VOICE`, `TTS_RESPONSE_FORMAT`.
Если `LLM_BASE_URL` не задан, текущий TTS-адаптер использует OpenRouter endpoint
для всех трёх значений; для OpenAI следует явно указать `https://api.openai.com/v1`.
Fish Audio в текущем коде не реализован, `FISH_*` не являются настройками приложения.
При сбое синтеза оркестратор отправляет текст.

## Kafka

По умолчанию используется in-memory шина. Для Kafka задать `MESSAGE_BUS=kafka`,
`KAFKA_BOOTSTRAP_SERVERS` и при необходимости `KAFKA_GROUP_ID`; Docker-профиль —
`docker compose --profile kafka up --build`. Maintain памяти пока выполняется
в consume-цикле, а state batching/orchestrator остаётся в памяти процесса.
Особенности масштабирования — в [ADR 0001](adr/0001-module-consistency.md).

## Проверки

CI использует SQLite, fake SDK, stub-провайдеры и детерминированные RNG/Hypothesis.
Рабочие аккаунты и платные API в CI не вызываются. Старые E2E-заглушки, которые
проходили без получения события, удалены; реальная доставка Telegram/Instagram
не считается проверенной этим набором. Для внешних E2E нужен отдельный полноценно
подключённый стенд с тестовыми аккаунтами и обязательными assertions доставки.
