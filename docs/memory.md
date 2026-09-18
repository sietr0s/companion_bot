# Память диалога

Модуль `memory` хранит переписку, rolling summary и векторный индекс **по темам**, не по батчам ответа. Батчер (`batching`) к нарезке тем не относится: он только копит входящие, чтобы бот ответил пачкой.

## Слои

| Слой | Что это | Когда обновляется |
|------|---------|-------------------|
| `messages` | Каждое входящее/исходящее, `sequence_number` | Сразу в `process_batch` / `update_memory` |
| `summary_states.current_summary` | Сжатая история | Если `last_sequence - checkpoint >= 50` |
| `summary_states.cluster_checkpoint` | Последний seq **закрытой** темы | После успешной кластеризации |
| `vector_records` | Одна строка = одна закрытая тема | После кластеризации; эмбеддинг от **названия темы** |

Батч ответа в вектор не пишется.

## Сохранение

Разговор уникален по `(channel, account_id, chat_id)`: два аккаунта бота с одним человеком не делят историю. Тот же ключ у in-memory батчера.

`memory.command.process_batch` (входящие) и `memory.command.update_memory` (исходящие, только `delivered`):

1. Дописать сообщения, увеличить `last_sequence_number`.
2. Сразу опубликовать `memory.event.batch.processed` / `memory.event.memory.updated` — ответный пайплайн не ждёт индекс.
3. Опубликовать `memory.command.maintain`. Хендлер **ждёт** `_run_maintain` (не `create_task`); на одном `conversation_id` maintain сериализуется lock'ом. На Kafka это занимает consume-цикл, пока кластеризация/summary не закончатся.

`maintain`: `_maybe_cluster`, затем при пороге 50 с прошлого summary checkpoint — `summarize`. До 3 попыток разобрать JSON кластера. Ошибка **не откатывает** сообщения.

## Кластеризация (`_maybe_cluster`)

Окно: все сообщения разговора с `sequence_number > cluster_checkpoint` (входящие и исходящие вместе).

- Меньше **20** сообщений — ничего не делать.
- Иначе LLM (`cluster_topics`) получает строки `seq|User|text` / `seq|Assistant|text` и должен вернуть JSON:

```json
[
  {"topic": "Проблема с сервером", "ids": [12, 13, 14], "kind": "topic"}
]
```

`kind`: `topic` или `noise`. `ids` — `sequence_number` из окна, непрерывные, без пересечений, покрывают всё окно.

Код (`clustering.py`) парсит JSON и режет блоки:

- **Закрытые** — все, кроме блока, который содержит последний seq окна. Их индексируем.
- **Открытый** — хвост текущей темы. Checkpoint на него не двигается, сообщения остаются в следующем окне.
- Окно **≥ 50** (`CLUSTER_HARD_CAP`) — закрыть все блоки, в `extra_data.partial = true`.
- Дыры, пересечения, чужие id — тик отменяется, индекс не трогаем.
- `noise` двигает checkpoint, вектор не создаёт.

Индекс закрытой темы:

- `VectorRecord.text` = название темы (UI и `retrieve_post`).
- `VectorRecord.kind` = `topic` или `reference` (фильтр поиска в SQL).
- `embedding` = `embed([title + текст блока], role="document")`, тело обрезается (`TOPIC_EMBED_MAX_CHARS`).
- `extra_data`: `kind`, `seq_from`, `seq_to`, `partial`.

## Сборка контекста (`build_context`)

Память отдаёт структуру, не готовую строку промпта:

- `recent: list[Batch]` — last N сообщений, сгруппированные по `message_batches` (пачка одной роли).
- `retrieved` / `references: list[Topic]` — `title` + `batches` в диапазоне `seq_from…seq_to`.
- `summary` — rolling summary.

1. Last N сообщений + summary.
2. `retrieve_pre` по хвосту диалога → query.
3. `embed` → `search_similar` (`kind=topic` в чате, `kind=reference` глобально).
4. `retrieve_post` оставляет точные совпадения названий.
5. Тема, целиком лежащая в last N, отбрасывается; пересечение режется до `recent_min_seq - 1`.
6. Сообщения темы грузятся из `messages` и группируются в `Batch` по `batch_id`.

Промпт (title + `User: a<next_message>b`) собирает модуль LLM (`src/modules/llm/formatting.py`).

Свежая незакрытая тема в индекс ещё не попала: она в `recent`.

Админка: `GET /api/v1/public/memory/conversations/{id}/topics` — закрытые темы без эмбеддинга; `GET .../topics/{topic_id}` — сообщения диапазона `seq_from…seq_to`.

## Константы

`src/modules/memory/constants.py`:

| Имя | Значение | Смысл |
|-----|----------|--------|
| `CLUSTER_MIN_MESSAGES` | 20 | Минимальное окно для вызова LLM-кластеризатора |
| `CLUSTER_HARD_CAP` | 50 | Форс-закрытие, даже если тема не кончилась |
| `CLUSTER_RETRIES` | 3 | Повторы parse JSON кластера |
| `SUMMARY_THRESHOLD` | 50 | Rolling summary |
| `VECTOR_TOP_K` | 10 | Сколько тем достать из индекса |
| `RETRIEVE_PRE_WINDOW` | 8 | Сколько последних реплик диалога уходит в retrieve_pre |
| `DEFAULT_LAST_N` | 50 | Хвост диалога в промпт |
| `SNIPPET_MAX_MESSAGES` | 12 | Потолок реплик в Retrieved-сниппете |
| `TOPIC_EMBED_MAX_CHARS` | 400 | Сколько текста блока клеится к title для эмбеддинга |
| `EMBEDDING_DIM` | 1024 | Qwen3-Embedding |

Кластеризация: `memory.command.maintain` после save. Промпт: `src/modules/llm/prompts/cluster_topics.md`.

## Миграция

Актуальная схема — Alembic `20260918_baseline`: `create_all` по текущим моделям, unique conversation `(channel, account_id, chat_id)`. Инкрементальных ревизий нет. Нужен чистый volume: `docker compose down -v`.
