# Модели базы данных

## Общие поля

Все модели наследуются от `BaseModel` и автоматически получают:

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID (PK) | Первичный ключ, автогенерация `uuid4` |
| created_at | TIMESTAMP WITH TIME ZONE | Автоматически при INSERT (`server_default=now()`) |
| updated_at | TIMESTAMP WITH TIME ZONE | Автоматически при INSERT и UPDATE (`onupdate=now()`) |

---

## auth_account

Модуль: `src/modules/auth/models.py`

Учётная запись авторизации. Хранит минимум данных для аутентификации.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | Email пользователя |
| hashed_password | VARCHAR(255) | NOT NULL | Хэш пароля (bcrypt) |
| role | VARCHAR(20) | NOT NULL, DEFAULT 'user' | Роль: `user` или `admin` |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

### Индексы

- `auth_account_email_key` — уникальный индекс по `email`

---

## user_profile

Модуль: `src/modules/users/models.py`

Профиль пользователя. Связан с `auth_account` через `auth_id`, но **без ForeignKey** — модули изолированы.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор профиля |
| auth_id | UUID | UNIQUE, NOT NULL, INDEX | ID учётной записи из модуля auth |
| first_name | VARCHAR(100) | NULLABLE | Имя |
| last_name | VARCHAR(100) | NULLABLE | Фамилия |
| avatar_url | VARCHAR(500) | NULLABLE | URL аватара |
| bio | TEXT | NULLABLE | Описание |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

### Индексы

- `user_profile_auth_id_key` — уникальный индекс по `auth_id`

### Почему нет ForeignKey?

`auth_id` — обычный UUID без `ForeignKey("auth_account.id")`. Это ключевое архитектурное решение:

1. **Изоляция модулей** — каждый модуль может использовать свою БД
2. **Независимое масштабирование** — модуль users не блокирует таблицу auth
3. **Простой вынос в микросервис** — не нужно менять схему при разделении

Ссылочная целостность обеспечивается на уровне бизнес-логики: `auth_id` всегда берётся из JWT-токена, который подписан сервисом авторизации.

---

## telegram_account

Модуль: `src/modules/telegram_clients/models.py`

Telegram-аккаунт пользователя. Связан с `auth_account` через `auth_id` без ForeignKey.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор аккаунта |
| auth_id | UUID | NOT NULL, INDEX | ID пользователя из модуля auth (без FK) |
| phone | VARCHAR(20) | NOT NULL | Номер телефона |
| session_file | VARCHAR(500) | NOT NULL | Путь к SQLite session-файлу Telethon |
| is_connected | BOOLEAN | DEFAULT FALSE | Подключён ли сейчас |
| first_name | VARCHAR(100) | NULLABLE | Имя из Telegram |
| last_name | VARCHAR(100) | NULLABLE | Фамилия из Telegram |
| username | VARCHAR(100) | NULLABLE | Username |
| telegram_id | BIGINT | NULLABLE | ID в Telegram (заполняется после авторизации) |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

### Индексы

- `ix_telegram_account_auth_id` — индекс по `auth_id`

---

## notification_template

Модуль: `src/modules/notifications/models.py`

Шаблон уведомления (Jinja2). Хранится в БД, может переопределять файловые шаблоны.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Имя шаблона (`welcome`, `password_reset`) |
| channel | VARCHAR(20) | NOT NULL | Канал: `email`, `sms` |
| subject_template | TEXT | NULLABLE | Jinja2-шаблон темы (для email) |
| body_template | TEXT | NOT NULL | Jinja2-шаблон тела |
| is_active | BOOLEAN | DEFAULT TRUE | Включён ли шаблон |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

---

## notification_log

Модуль: `src/modules/notifications/models.py`

Лог отправленного уведомления. Хранит статус, отрендеренный текст и ошибки.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор |
| auth_id | UUID | NOT NULL, INDEX | ID пользователя (без FK) |
| channel | VARCHAR(20) | NOT NULL | `email`, `sms` |
| template_name | VARCHAR(100) | NOT NULL | Имя использованного шаблона |
| recipient | VARCHAR(255) | NOT NULL | Email/телефон получателя |
| subject | TEXT | NULLABLE | Отрендеренная тема |
| body | TEXT | NOT NULL | Отрендеренное тело |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | `pending`, `sent`, `failed` |
| error_message | TEXT | NULLABLE | Ошибка (если failed) |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

### Индексы

- `ix_notification_log_auth_id` — индекс по `auth_id`

---

## ER-диаграмма

```
┌──────────────────┐          ┌──────────────────────┐
│   auth_account   │          │    user_profile      │
├──────────────────┤          ├──────────────────────┤
│ id (UUID, PK)    │◄─ ─ ─ ─ │ auth_id (UUID, UQ)   │
│ email (UQ)       │  логич.  │ first_name           │
│ hashed_password  │  связь   │ last_name            │
│ role             │          │ avatar_url           │
│ created_at       │          │ bio                  │
│ updated_at       │          │ created_at           │
└──────────────────┘          │ updated_at           │
        │                     └──────────────────────┘
        │
        │  ┌──────────────────────────┐
        │  │    telegram_account      │
        │  ├──────────────────────────┤
        └──│ auth_id (UUID, INDEX)    │
           │ phone                    │
           │ session_file             │
           │ is_connected             │
           │ first_name               │
           │ last_name                │
           │ username                 │
           │ telegram_id (BIGINT)     │
           │ created_at               │
           │ updated_at               │
           └──────────────────────────┘
        │
        │  ┌──────────────────────────┐
        │  │    notification_log      │
        │  ├──────────────────────────┤
        └──│ auth_id (UUID, INDEX)    │
           │ channel                  │
           │ template_name            │
           │ recipient                │
           │ subject                  │
           │ body                     │
           │ status                   │
           │ error_message            │
           │ created_at               │
           │ updated_at               │
           └──────────────────────────┘

  ┌──────────────────────────┐
  │ notification_template    │
  ├──────────────────────────┤
  │ id (UUID, PK)            │
  │ name (UQ)                │
  │ channel                  │
  │ subject_template         │
  │ body_template            │
  │ is_active                │
  │ created_at               │
  │ updated_at               │
  └──────────────────────────┘

  ─ ─ ─  логическая связь (без ForeignKey)
```

---

## stored_file

Модуль: `src/modules/media/models.py`

Медиа-файл. Файлы независимы — не имеют владельца (`auth_id`), доступ контролируется через `is_public`.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор файла |
| filename | VARCHAR(255) | NOT NULL | Оригинальное имя файла |
| content_type | VARCHAR(100) | NOT NULL | MIME-тип (image/png, application/pdf) |
| size_bytes | BIGINT | NOT NULL | Размер в байтах |
| storage_key | VARCHAR(500) | UNIQUE, NOT NULL | Ключ в хранилище (ab/cd/uuid.ext) |
| is_public | BOOLEAN | DEFAULT FALSE | Публичный доступ |
| created_at | TIMESTAMP | NOT NULL | Дата загрузки |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

### Индексы

- `stored_file_storage_key_key` — уникальный индекс по `storage_key`

### Почему нет владельца?

Файлы спроектированы как независимые ресурсы для упрощения межмодульного доступа:

1. **Межмодульное взаимодействие** — любой модуль может получить файл через `/internal/media/{id}`
2. **Упрощённая модель** — не нужно проверять права владельца при доступе
3. **Гибкость** — `is_public` контролирует публичный доступ, network-level — внутренний

При необходимости связи "файл-владелец" создаётся отдельная таблица-связка в модуле-потребителе.
```
