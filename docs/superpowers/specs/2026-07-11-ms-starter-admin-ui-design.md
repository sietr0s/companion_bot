# Дизайн админ-панели для ms_starter (Modular Monolith)

**Дата**: 2026-07-11
**Статус**: Черновик / Идея

## О проекте

**ms_starter** — модульный монолит на Python + FastAPI. Сервис предоставляет ~55 REST API эндпоинтов, объединённых в 8 бизнес-модулей. Фронтенда нет — нужна полноценная SPA-админка.

## Технологический стек

- **Frontend**: React 18+ / TypeScript
- **UI Library**: Ant Design 5.x
- **Сборка**: Vite
- **HTTP-клиент**: Axios или React Query (TanStack Query)
- **Роутинг**: React Router v6
- **Стейт-менеджмент**: Zustand или React Context (для токена/авторизации)
- **Формы**: Ant Design Form + React Hook Form (опционально)
- **Дата-таблицы**: Ant Design Table (с фильтрацией, сортировкой, пагинацией)

## Структура навигации (боковое меню)

### 1. Дашборд (Dashboard)
- Сводная статистика: количество пользователей, файлов, TG-аккаунтов, отправленных уведомлений
- Графики/виджеты активности (регистрации, загрузки, классификации)
- Последние события / лог активности

### 2. Аутентификация (Auth)
- **Страница входа** (`/login`): форма с полями identifier + password, кнопка "Войти"
- **Страница регистрации** (`/register`): форма с identifier, выбор типа (email/phone/telegram), password
- **Смена пароля** (`/change-password`): форма с current_password + new_password
- **Удаление аккаунта** (`/delete-account`): подтверждение с паролем

### 3. Пользователи (Users)
- **Список пользователей** (`/users`): таблица (ID, auth_id, имя, дата создания), поиск, пагинация
- **Профиль пользователя** (`/users/me`): просмотр/редактирование (first_name, last_name, avatar_url, bio)
- **Telegram-профиль** (`/users/me/telegram`): просмотр привязанного Telegram (telegram_id, username)

### 4. Медиа-файлы (Media)
- **Список файлов** (`/media`): таблица (filename, content_type, size, is_public, дата)
- **Загрузка файла** (`/media/upload`): drag-and-drop, форма с is_public toggle
- **Просмотр файла** (`/media/:id`): метаданные + скачивание
- **Удаление файла**: кнопка в таблице с confirm-диалогом

### 5. Telegram-клиенты (Telegram)
- **Список аккаунтов** (`/telegram`): таблица (phone, is_connected, username, статус)
- **Подключение аккаунта** (`/telegram/connect`): пошаговый мастер:
  - Шаг 1: ввод номера телефона
  - Шаг 2: ввод SMS-кода
  - Шаг 3: ввод 2FA пароля (если требуется)
- **Просмотр чатов** (`/telegram/:id/chats`): список чатов с типом (группа/личный/канал)
- **Просмотр сообщений** (`/telegram/:id/chats/:chatId`): лента сообщений с медиа
- **Настройки аккаунта** (`/telegram/:id/settings`): toggle read_groups, read_personal, read_channels, whitelist_chat_ids

### 6. Классификатор (Classifier)
- **Список категорий** (`/classifier/categories`): таблица (name, slug, description, is_active)
- **Создание/редактирование категории**: форма с name, slug (авто-генерация), description, is_active
- **Удаление категории**: confirm-диалог

### 7. Уведомления (Notifications)
- **Список шаблонов** (`/notifications/templates`): таблица (name, channel, is_active)
- **Создание/редактирование шаблона**: форма с name, channel (select), subject_template, body_template (textarea/editor), is_active
- **История отправок** (`/notifications/history`): таблица (auth_id, channel, template_name, status, дата)
- **Просмотр лога** (`/notifications/history/:id`): детали отправки

### 8. Job Matcher (Вакансии)
- **Список подписок** (`/job-matcher/subscriptions`): таблица (keywords, categories, salary range, is_active)
- **Создание подписки**: форма с keywords, выбор категорий, min/max salary, locations
- **Список вакансий** (`/job-matcher/offers`): таблица (title, tags, salary, location, source)
- **Просмотр вакансии** (`/job-matcher/offers/:id`): детали + matched subscriptions

## Общие требования к UI/UX

### Макет (Layout)
- **Слева**: collapsible sidebar с навигацией (иконка + label)
- **Сверху**: header с логотипом, именем пользователя, кнопкой выхода
- **Центр**: контентная область с breadcrumbs
- **Адаптивность**: sidebar сворачивается в hamburger на мобильных

### Токены дизайна (Ant Design Theme)
- **Цветовая схема**: тёмная тема (dark mode) как основная, светлая — опционально
- **Primary color**: #1677ff (Ant Design default) или кастомный брендовый цвет
- **Типографика**: system font stack (Segoe UI, Roboto, sans-serif)
- **Пространство**: Ant Design spacing tokens (padding, margin)

### Паттерны
- **Таблицы**: сортировка по колонкам, фильтры, пагинация (Ant Design Table)
- **Формы**: валидация на стороне клиента, loading states на submit, error messages
- **Модальные окна**: для подтверждения удаления, для быстрых форм
- **Уведомления**: Ant Design notification/message для success/error тостов
- **Пустые состояния**: Empty-компоненты с иконками и текстом
- **Ошибки**: ErrorBoundary, 404 страница, 500 страница

### Состояния загрузки
- Skeleton-компоненты для таблиц и карточек
- Spinner для кнопок и форм
- Progress bar для загрузки файлов

### Безопасность
- JWT-токен хранится в httpOnly cookie или localStorage
- Interceptor на каждый запрос: добавляет Authorization header
- При 401 — редирект на /login
- Logout — очистка токена + редирект

## Структура проекта (рекомендуемая)

```
frontend/
├── public/
├── src/
│   ├── api/              # API-клиенты (axios instances, endpoints)
│   │   ├── auth.ts
│   │   ├── users.ts
│   │   ├── media.ts
│   │   ├── telegram.ts
│   │   ├── classifier.ts
│   │   ├── notifications.ts
│   │   └── jobMatcher.ts
│   ├── components/       # Переиспользуемые компоненты
│   │   ├── Layout/       # AppLayout, Sidebar, Header
│   │   ├── common/       # PageHeader, ConfirmDialog, EmptyState
│   │   └── ...
│   ├── pages/            # Страницы по модулям
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── users/
│   │   ├── media/
│   │   ├── telegram/
│   │   ├── classifier/
│   │   ├── notifications/
│   │   └── jobMatcher/
│   ├── hooks/            # Кастомные React hooks
│   ├── store/            # Состояние (auth, theme)
│   ├── types/            # TypeScript типы (интерфейсы для API)
│   ├── utils/            # Хелперы, форматтеры
│   ├── App.tsx
│   ├── main.tsx
│   └── router.tsx
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

## API-эндпоинты для интеграции

### Auth (public)
| Метод | Путь | Описание |
|-------|------|----------|
| POST | /api/v1/public/auth/register | Регистрация |
| POST | /api/v1/public/auth/login | Вход |
| PATCH | /api/v1/public/auth/me/password | Смена пароля |
| DELETE | /api/v1/public/auth/me | Удаление аккаунта |

### Users (public)
| Метод | Путь | Описание |
|-------|------|----------|
| POST | /api/v1/public/users/ | Создать профиль |
| GET | /api/v1/public/users/me | Получить профиль |
| PATCH | /api/v1/public/users/me | Обновить профиль |
| DELETE | /api/v1/public/users/me | Удалить профиль |
| GET | /api/v1/public/users/me/telegram | Получить Telegram-профиль |

### Media (public)
| Метод | Путь | Описание |
|-------|------|----------|
| POST | /api/v1/public/media/upload | Загрузить файл |
| GET | /api/v1/public/media/{file_id} | Метаданные файла |
| GET | /api/v1/public/media/{file_id}/download | Скачать файл |
| DELETE | /api/v1/public/media/{file_id} | Удалить файл |

### Telegram Clients (public)
| Метод | Путь | Описание |
|-------|------|----------|
| POST | /api/v1/public/telegram/auth/phone | Шаг 1: номер |
| POST | /api/v1/public/telegram/auth/code | Шаг 2: код |
| POST | /api/v1/public/telegram/auth/password | Шаг 3: 2FA |
| GET | /api/v1/public/telegram/ | Список аккаунтов |
| GET | /api/v1/public/telegram/{account_id} | Аккаунт детально |
| DELETE | /api/v1/public/telegram/{account_id} | Удалить аккаунт |
| GET | /api/v1/public/telegram/{account_id}/chats | Список чатов |
| GET | /api/v1/public/telegram/{account_id}/chats/{chat_id}/messages | Сообщения |
| GET/POST/PUT/DELETE | /api/v1/public/telegram/{account_id}/settings | Настройки |

### Classifier (public)
| Метод | Путь | Описание |
|-------|------|----------|
| POST | /api/v1/public/classifier/categories | Создать категорию |
| GET | /api/v1/public/classifier/categories | Список категорий |
| PATCH | /api/v1/public/classifier/categories/{slug} | Обновить категорию |
| DELETE | /api/v1/public/classifier/categories/{slug} | Удалить категорию |

### Notifications (public)
| Метод | Путь | Описание |
|-------|------|----------|
| POST | /api/v1/public/notifications/templates/ | Создать шаблон |
| GET | /api/v1/public/notifications/templates/ | Список шаблонов |
| GET | /api/v1/public/notifications/templates/{id} | Шаблон детально |
| PATCH | /api/v1/public/notifications/templates/{id} | Обновить шаблон |
| DELETE | /api/v1/public/notifications/templates/{id} | Удалить шаблон |
| GET | /api/v1/public/notifications/history/ | История отправок |
| GET | /api/v1/public/notifications/history/{id} | Лог детально |

### Health
| Метод | Путь | Описание |
|-------|------|----------|
| GET | /health | Health check |