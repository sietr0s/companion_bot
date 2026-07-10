# Дизайн модели TelegramChatState

**Дата:** 2026-07-09  
**Модуль:** telegram_clients  
**Статус:** Утверждён

---

## Цель

Добавить модель для хранения состояния чтения сообщений в чатах Telegram. Модель позволяет отслеживать ID последнего прочитанного сообщения для каждого чата каждого Telegram-аккаунта.

---

## Архитектурное решение

### Модель данных

**Имя таблицы:** `telegram_chat_state`

**Поля:**
| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Primary key |
| `account_id` | UUID | ForeignKey на `telegram_account.id` (CASCADE delete) |
| `chat_id` | BigInteger | ID чата в Telegram |
| `created_at` | DateTime | Дата создания записи (из BaseModel) |
| `updated_at` | DateTime | Дата последнего обновления (из BaseModel) |

**Ограничения:**
- `UniqueConstraint('account_id', 'chat_id')` — одна запись на чат для каждого аккаунта
- Индексы: `account_id`, `chat_id` (для ускорения поиска)

### Репозиторий

**Класс:** `TelegramChatStateRepository`

**Методы:**
1. `get_by_account_and_chat(session, account_id, chat_id)` → `TelegramChatState | None`
   - Получить состояние чтения для конкретного чата
2. `upsert_last_read(session, account_id, chat_id, message_id)` → `TelegramChatState`
   - Создать новую запись или обновить существующую (atomic upsert)
3. `get_all_by_account(session, account_id)` → `list[TelegramChatState]`
   - Получить все состояния чтения для аккаунта

### Сервис

**Класс:** `TelegramClientService` (расширение текущего)

**Методы:**
1. `get_chat_state(session, account_id, auth_id, chat_id)` → `TelegramChatState`
   - Получить состояние с проверкой принадлежности аккаунта пользователю
   - Выбрасывает `NotFoundError` если аккаунт не найден
2. `update_last_read(session, account_id, auth_id, chat_id, message_id)` → `TelegramChatState`
   - Обновить ID последнего прочитанного сообщения
   - Выбрасывает `NotFoundError` если аккаунт не найден
3. `get_all_chats_state(session, account_id, auth_id)` → `list[TelegramChatState]`
   - Получить все состояния чтения для аккаунта
   - Выбрасывает `NotFoundError` если аккаунт не найден

---

## Варианты реализации

### Рассмотренные альтернативы

**1. Детальное отслеживание (отклонено)**
- Хранить запись для каждого сообщения с флагом `is_read`
- *Почему отклонено:* Избыточно для текущей задачи, большой объём данных

**2. Привязка к auth_id (отклонено)**
- Хранить состояние на пользователя, а не на аккаунт
- *Почему отклонено:* Не соответствует архитектуре модуля, где настройки привязаны к `account_id`

**3. Расширенная модель с `last_read_at` (отклонено)**
- Добавить поле времени последнего чтения
- *Почему отклонено:* Достаточно `updated_at` из базовой модели

---

## Интеграция

### Миграция БД
Создать новую миграцию Alembic:
```python
op.create_table(
    'telegram_chat_state',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('account_id', sa.UUID(), nullable=False),
    sa.Column('chat_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['telegram_account.id'], ondelete='CASCADE'),
    sa.UniqueConstraint('account_id', 'chat_id'),
)
op.create_index('ix_telegram_chat_state_account_id', 'telegram_chat_state', ['account_id'])
op.create_index('ix_telegram_chat_state_chat_id', 'telegram_chat_state', ['chat_id'])
```

### Обновление service.py
Добавить методы в `TelegramClientService` для работы с состоянием чтения.

### Обновление repository.py
Создать `TelegramChatStateRepository` с методами для работы с БД.

---

## Тестирование

**Юнит-тесты:**
- Репозиторий: CRUD-операции, upsert, уникальность пары (account_id, chat_id)
- Сервис: проверка прав доступа (auth_id), обработка NotFoundError

**Интеграционные тесты:**
- Обновление состояния при получении новых сообщений
- Корректная работа cascade delete при удалении аккаунта

---

## Чеклист реализации

- [ ] Создать модель `TelegramChatState` в `models.py`
- [ ] Создать репозиторий `TelegramChatStateRepository` в `repository.py`
- [ ] Добавить методы в сервис `TelegramClientService` в `service.py`
- [ ] Создать миграцию Alembic
- [ ] Добавить тесты на репозиторий
- [ ] Добавить тесты на сервис
- [ ] Закоммитить изменения
