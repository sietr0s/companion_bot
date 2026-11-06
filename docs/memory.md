# Память диалога

`memory` хранит историю, rolling summary и векторный индекс закрытых тем.
Входящий батч — единица накопления сообщений; он не является темой для retrieval.
Разговор имеет ключ `(channel, account_id, chat_id)`.

## Данные

| Таблица | Содержимое |
| --- | --- |
| `conversations` | Идентификатор канала/аккаунта/чата, sequence counter, активность |
| `message_batches` | Сохранённые группы сообщений одной роли |
| `messages` | Текст, direction, message_type, batch_id, sequence_number |
| `summary_states` | `current_summary`, summary `checkpoint`, `cluster_checkpoint` |
| `vector_records` | `text`, `kind`, `embedding`, `seq_from`, `seq_to`, `partial` |

`kind`, диапазон и `partial` — отдельные колонки; поля `extra_data` нет.
Сохранённый текст включает display-разметку reply/forward; ORM-представление
не строит промпт для провайдера.

## Слои и структура

`schemas/api.py` и `schemas/events.py` — транспортные DTO. `domain.py` содержит
HistoryMessage, HistoryWindow, IndexedTopic, RollingSummary и правила разбиения
окна. Репозиторий возвращает доменные снимки: после закрытия SQL-сессии они
остаются доступны без lazy loading. Преобразование ORM находится на границе
репозитория; отдельного `mapping.py` нет. Внутренние сервисы не импортируют
ORM и транспортные DTO. SQL-типы находятся рядом с `models.py`.

Сервисы лежат только в `services/`, helpers — в `utils.py`. Менеджерские роутеры
разделены по сущностям в `routers/manager/`. Полные правила —
[ADR 0002](adr/0002-module-boundaries-and-layout.md).

## Запись и обслуживание

`MemoryService` экспортируется из `src.modules.memory.services`.
Фасад `services/pipeline.py` принимает команды и публикует события:

1. `process_batch` получает/создаёт разговор и сохраняет входящие.
2. `update_memory` сохраняет исходящие только при `delivery_status=delivered`.
3. `MessageBatchRepository.append_messages` фиксирует batch, сообщения и увеличение
   sequence counter одной транзакцией. При сбое не остаётся половины batch.
4. После commit публикуются `memory.event.batch.processed` /
   `memory.event.memory.updated`, затем команда `memory.command.maintain`.

`services/maintenance.py` сериализует maintain для разговора локальным lock.
Сначала выполняется кластеризация, затем при пороге — summary. Обработчик ждёт
maintain; Kafka consume-цикл на это время занят. Это не распределённая блокировка.
Ошибка обслуживания не отменяет уже сохранённую историю.

Summary строится из сообщений после предыдущего checkpoint и не дальше
`current_sequence` команды. Порог обновления — 50 сообщений.

## Индексация тем

Окно — сообщения после `cluster_checkpoint`. Меньше 20 сообщений не кластеризуются.
При 50 и более сообщениях обрабатываются первые 50, с принудительным закрытием.
LLM получает `seq|User|text` / `seq|Assistant|text` и возвращает блоки:

```json
[{"topic": "Проблема с сервером", "ids": [12, 13, 14], "kind": "topic"}]
```

`utils.py` разбирает ответ LLM, а `domain.py` фильтрует ID вне окна, устраняет пересечения,
разбивает разрывы на непрерывные диапазоны и заполняет остаток как `noise`.
Одно сообщение не образует тему. После нормализации проверяется точное покрытие
окна без повторов. Невалидный результат повторяется до трёх раз; при исчерпании
попыток индекс и checkpoint остаются прежними.

Последняя тема остаётся открытой и попадёт в следующее окно. Trailing noise
закрывается сразу. При hard cap закрываются все блоки, `partial=True`.
Noise продвигает checkpoint, но не создаёт вектор.

`services/indexing.py` используется и live-maintenance, и reference-import:

- `VectorRecord.text` — заголовок для UI и reranking.
- Embedding строится по заголовку **и тексту блока**, до 400 символов тела.
- Все embeddings должны соответствовать числу тем до начала записи.
- Векторы окна и cluster checkpoint фиксируются одной транзакцией.

## Построение контекста

`services/context.py` возвращает доменный `ConversationContext`; фасад pipeline
оборачивает его в `ContextBuiltEvent`:

- `summary` — rolling summary;
- `recent: list[Batch]` — последние N сообщений, сгруппированные по batch_id;
- `retrieved: list[Topic]` — релевантные темы текущего разговора;
- `references: list[Topic]` — глобальные эталоны `kind=reference`.

`retrieve_pre` использует последние 8 реплик для короткого query. Query embedding
ищет до 10 тем каждого вида, затем `retrieve_post` сохраняет только точные
совпадения названий. Уже включённая в recent часть темы обрезается; из одного
retrieved диапазона берутся максимум 12 сообщений. Ошибка AI retrieval оставляет
recent и summary, но убирает retrieved/references.

Готовый prompt строится в `llm/utils.py`. Память зависит от
`MemoryIntelligence`, не от конкретного LLMService или SDK.

## Reference-import и HTTP

Импорт — отдельная developer-команда, а не runtime-сервис памяти:

```bash
python -m scripts.import_reference export.json
python -m scripts.import_reference export.json --replace
```

`--replace` заменяет историю импортированного разговора и сбрасывает checkpoints.
Импорт ограничен `account_id=None`, поэтому не заменяет live-историю аккаунта.


`scripts.import_reference.load_reference_export` читает Telegram Desktop JSON, объединяет
текстовые сущности и индексирует окна до 100 сообщений как `kind=reference`.
В текущем формате отрицательный chat_id отделяет импорт от live-истории; направление
peer-сообщений используется как стиль исходящих эталонов. При неразбираемом окне
импорт продвигает checkpoint и продолжает со следующего, с записью warning.
Это отличается от live-maintenance, где неудачное окно остаётся для повтора.

Manager CRUD (требуют admin JWT) — `/api/v1/public/memory/*`. Темы без embedding:

- `GET /conversations/{id}/topics`
- `GET /conversations/{id}/topics/{topic_id}` — с сообщениями диапазона.

Оба пути указаны относительно `/api/v1/public/memory`. `TopicQueryService` не
создаёт AI-провайдер: чтение уже сохранённых тем не требует API key.

## Настройки и схема

Пороговые константы — `src/modules/memory/constants.py`. Размерность embedding —
1024 для выбранного Qwen; изменение модели/размерности требует отдельной миграции.
Актуальная ревизия — `20260918_baseline`; старые ORM-таблицы DB-батчера в неё не
входят. Удаление неиспользуемых Python-моделей не удаляет таблицы существующей БД.

Для запуска применять `alembic upgrade head`. Не сбрасывать volume автоматически:
несовместимая история миграций требует отдельного плана и резервной копии.
Ограничения outbox, идемпотентности и нескольких worker описаны в
[ADR 0001](adr/0001-module-consistency.md).
