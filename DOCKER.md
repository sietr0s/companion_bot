# Docker Deployment Guide

Быстрый старт проекта с помощью Docker Compose.

## Предварительные требования

- Docker Engine 24.0+
- Docker Compose 2.20+

## Быстрый старт

### 1. Настройка окружения

```bash
# Скопируйте пример конфигурации
cp .env.docker.example .env

# Отредактируйте .env и настройте переменные
# ОБЯЗАТЕЛЬНО: смените JWT_SECRET_KEY на случайный ключ
# python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Запуск приложения (без Kafka)

```bash
# Запуск PostgreSQL и приложения
docker-compose up -d

# Просмотр логов
docker-compose logs -f app

# Остановка
docker-compose down
```

### 3. Запуск с Kafka (для микросервисов)

```bash
# Запуск всех сервисов включая Kafka и Zookeeper
docker-compose --profile kafka up -d

# Просмотр логов Kafka
docker-compose --profile kafka logs -f kafka

# Остановка
docker-compose --profile kafka down
```

### 4. Запуск pgAdmin (для управления БД)

```bash
# Запуск pgAdmin вместе с базой данных
docker-compose --profile admin up -d

# Откройте браузер: http://localhost:5050
# Логин: admin@example.com
# Пароль: admin (или из .env)

# Остановка
docker-compose --profile admin down
```

## Профили

docker-compose.yml содержит следующие профили:

| Профиль | Описание | Сервисы |
|---------|----------|---------|
| `default` | Базовая конфигурация | app, db |
| `kafka` | С шиной сообщений Kafka | kafka, zookeeper |
| `admin` | Панель управления БД | pgadmin |

## Команды

### Сборка и запуск

```bash
# Полная пересборка (без кэша)
docker-compose build --no-cache
docker-compose up -d

# Перезапуск приложения
docker-compose restart app

# Остановка и удаление всех контейнеров + томов
docker-compose down -v
```

### Отладка

```bash
# Вход в контейнер приложения
docker-compose exec app bash

# Выполнение миграций БД
docker-compose exec app alembic upgrade head

# Проверка здоровья приложения
curl http://localhost:8000/docs

# Просмотр логов
docker-compose logs -f app
docker-compose logs -f db
```

### Работа с БД

```bash
# Подключение к PostgreSQL из хоста
psql postgresql://postgres:postgres@localhost:5432/modular_monolith

# Бэкап базы данных
docker-compose exec db pg_dump -U postgres modular_monolith > backup.sql

# Восстановление из бэкапа
docker-compose exec -T db psql -U postgres modular_monolith < backup.sql
```

## Переменные окружения

Основные переменные в `.env`:

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `JWT_SECRET_KEY` | Секретный ключ для JWT | (смените!) |
| `MESSAGE_BUS` | Реализация шины: `in_memory` или `kafka` | `in_memory` |
| `TG_API_ID` | Telegram API ID | - |
| `TG_API_HASH` | Telegram API Hash | - |
| `DEBUG` | Режим отладки | `False` |

## Структура томов

- `postgres_data` - данные PostgreSQL
- `pgadmin_data` - данные pgAdmin
- `./sessions` - Telegram session файлы (хост)

## Health Checks

Сервисы имеют health checks:

- **db**: Проверка готовности PostgreSQL (10s интервал)
- **app**: Проверка `/docs` эндпоинта (30s интервал)

Приложение автоматически начнёт работу после готовности БД.

## Обновление

```bash
# Остановка
docker-compose down

# Обновление образа
docker-compose pull
docker-compose build

# Запуск
docker-compose up -d
```

## Удаление

```bash
# Полная очистка (контейнеры, тома, кэш)
docker-compose down -v
docker system prune -f
```

## Troubleshooting

### Приложение не запускается

```bash
# Проверка логов
docker-compose logs app

# Проверка здоровья БД
docker-compose exec db pg_isready -U postgres
```

### Проблемы с подключением к БД

Убедитесь, что:
1. БД полностью запустилась (`docker-compose logs db`)
2. Переменные окружения правильные
3. Порт 5432 не занят другим сервисом

### Kafka не подключается

1. Убедитесь, что запущен с профилем: `docker-compose --profile kafka up`
2. Проверьте `MESSAGE_BUS=kafka` в `.env`
3. Проверьте логи: `docker-compose logs zookeeper kafka`

## Разработка

Для разработки с hot-reload:

```bash
# Создать Dockerfile.dev с mount кода
# Или использовать bind mounts в docker-compose.yml
volumes:
  - ./src:/app/src
  - ./tests:/app/tests
```
