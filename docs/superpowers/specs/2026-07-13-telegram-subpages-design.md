# Telegram: Разделение на подстраницы

**Дата:** 2026-07-13
**Статус:** Черновик

## Мотивация

Текущая `TelegramPage.tsx` — монолитная страница, совмещающая:
- Подключение аккаунта (SMS/QR)
- Список аккаунтов
- Список чатов выбранного аккаунта
- Сообщения выбранного чата
- Настройки чтения аккаунта

Страница содержит ~350 строк, 7 мутаций, 5 query-запросов и 10+ состояний. Это затрудняет поддержку, навигацию и дальнейшее расширение (например, добавление медиа-вкладки).

## Цель

Разделить Telegram-блок на 3 отдельные подстраницы:

| Роут | Компонент | Назначение |
|------|-----------|------------|
| `/telegram` | `TelegramAccountsPage` | Подключение аккаунта + таблица аккаунтов |
| `/telegram/:accountId/chats` | `TelegramChatsPage` | Чаты (слева) + сообщения (справа) |
| `/telegram/:accountId/settings` | `TelegramSettingsPage` | Настройки чтения аккаунта |

## Архитектура

### Роутинг

```tsx
// router.tsx
<Route path="telegram" element={<TelegramAccountsPage />} />
<Route path="telegram/:accountId/chats" element={<TelegramChatsPage />} />
<Route path="telegram/:accountId/settings" element={<TelegramSettingsPage />} />
```

### Навигация (боковое меню)

Пункт "Telegram" в Sider ведёт на `/telegram` (список аккаунтов).

При клике на аккаунт в таблице — переход на `/telegram/:accountId/chats` (через `navigate()`).

На странице чатов/сообщений — кнопка "Настройки", ведущая на `/telegram/:accountId/settings`.

На странице настроек — кнопка "Назад к чатам" на `/telegram/:accountId/chats`.

### Breadcrumbs

- `/telegram` → `Telegram`
- `/telegram/:accountId/chats` → `Telegram / {phone} / Chats`
- `/telegram/:accountId/settings` → `Telegram / {phone} / Settings`

### Компоненты

#### TelegramAccountsPage

Выделяется из текущей `TelegramPage.tsx`:
- **Подключение аккаунта** (SMS/QR) — без изменений
- **Таблица аккаунтов** — без изменений, но клик по строке → `navigate()` вместо `setSelectedAccountId`
- **Удаление аккаунта** — после удаления редирект на `/telegram`, если мы были на подстранице этого аккаунта

#### TelegramChatsPage

Выделяется из текущей `TelegramPage.tsx`:
- URL: `/telegram/:accountId/chats`
- Загрузка аккаунта по `accountId` из URL (для отображения номера телефона в breadcrumbs)
- **Список чатов** (слева) — как сейчас
- **Сообщения** (справа) — как сейчас
- Кнопка "Настройки" в заголовке страницы → `/telegram/:accountId/settings`

#### TelegramSettingsPage

Выделяется из текущей `TelegramPage.tsx`:
- URL: `/telegram/:accountId/settings`
- Загрузка аккаунта по `accountId` (для breadcrumbs)
- **Форма настроек** — как сейчас (read_groups, read_personal, read_channels, whitelist)
- Кнопка "Назад к чатам" → `/telegram/:accountId/chats`

### Состояния и переходы

| Действие | Текущее поведение | Новое поведение |
|----------|-------------------|-----------------|
| Клик по аккаунту | `setSelectedAccountId(id)` | `navigate(/telegram/${id}/chats)` |
| Удаление аккаунта | `setSelectedAccountId(null)` | `navigate(/telegram)` |
| Подключение аккаунта | остаётся на месте | остаётся на месте |
| Кнопка "Настройки" | — (настройки рядом с чатами) | `navigate(/telegram/${id}/settings)` |
| Кнопка "Назад к чатам" | — | `navigate(/telegram/${id}/chats)` |

### API-запросы (без изменений)

Все queryKey и мутации остаются теми же. Единственное изменение — `selectedAccountId` берётся из `useParams()` вместо `useState()`.

## План реализации

1. Создать `TelegramAccountsPage.tsx` — вырезать из `TelegramPage.tsx` блок с подключением + таблицей
2. Создать `TelegramChatsPage.tsx` — вырезать блок с чатами + сообщениями
3. Создать `TelegramSettingsPage.tsx` — вырезать блок с настройками
4. Обновить `router.tsx` — добавить 3 роута вместо 1
5. Обновить `ProtectedLayout.tsx` — обновить breadcrumbs для новых путей
6. Удалить старый `TelegramPage.tsx`
7. Проверить сборку (`npm run build`)