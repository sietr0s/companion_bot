# Развёртывание приложения (Deployment)

Это руководство описывает процесс развёртывания приложения ms_starter в различных окружениях.

---

## Содержание

1. [Локальная разработка](#локальная-разработка)
2. [Docker Compose](#docker-compose)
3. [Production](#production)
4. [Миграции БД](#миграции-бд)
5. [Мониторинг и логирование](#мониторинг-и-логирование)

---

## Локальная разработка

### Требования

- Python 3.11+
- PostgreSQL 15+
- pip или uv

### Быстрый старт

```bash
# 1. Клонирование репозитория
git clone <repository-url>
cd ms_starter

# 2. Создание виртуального окружения
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 3. Установка зависимостей
pip install -r requirements.txt

# 4. Настройка окружения
cp .env.example .env
# Отредактируйте .env, установите TG_API_ID, TG_API_HASH, JWT_SECRET_KEY

# 5. Запуск PostgreSQL (если не установлен локально)
docker-compose up -d db

# 6. Применение миграций
alembic upgrade head

# 7. Запуск сервера
uvicorn src.main:app --reload

# Swagger UI: http://localhost:8000/docs
```

---

## Docker Compose

### Базовый запуск (приложение + PostgreSQL)

```bash
docker-compose up -d
```

**Порты:**
- `8000:8000` — приложение
- `5432:5432` — PostgreSQL (только для разработки!)

**Тома:**
- `./sessions:/app/sessions` — сессии Telegram
- `./templates:/app/templates:ro` — шаблоны уведомлений

### С Kafka

```bash
docker-compose --profile kafka up -d
```

Запускает дополнительные сервисы:
- Zookeeper: `2181`
- Kafka: `9092`, `29092`

### С pgAdmin

```bash
docker-compose --profile admin up -d
```

**Важно:** Требуется установить `PGADMIN_PASSWORD` в `.env`!

```bash
# .env
PGADMIN_PASSWORD=your_secure_password_here
```

**Порт pgAdmin:** `${PGADMIN_PORT:-5151}:80`. По умолчанию интерфейс доступен
на [http://localhost:5151](http://localhost:5151). Порт можно изменить через
`PGADMIN_PORT` в env-файле.

---

## Production

### Требования к безопасности

1. **Смените все пароли по умолчанию:**
   ```bash
   # .env
   POSTGRES_PASSWORD=<secure-random-password>
   JWT_SECRET_KEY=<secure-random-key>
   PGADMIN_PASSWORD=<secure-random-password>
   ```

2. **Отключите создание таблиц при старте:**
   ```bash
   CREATE_TABLES_ON_STARTUP=False
   ```

3. **Не экспортируйте порт БД:**
   Удалите строку `ports: - "5432:5432"` из `docker-compose.yml` для БД.

4. **Используйте secrets:**
   Для Docker Swarm или Kubernetes используйте secrets для чувствительных данных.

### Переменные окружения для production

```bash
# БД
DB_HOST=postgres-service.internal
DB_PORT=5432
DB_USER=app_user
DB_PASSWORD=<secure-password>
DB_NAME=modular_monolith
DATABASE_POOL_SIZE=20

# JWT
JWT_SECRET_KEY=<cryptographically-secure-key>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Приложение
DEBUG=False
PORT=8000
CREATE_TABLES_ON_STARTUP=False

# Шина сообщений
MESSAGE_BUS=kafka
KAFKA_BOOTSTRAP_SERVERS=kafka-1:9092,kafka-2:9092,kafka-3:9092

# Telegram
TG_API_ID=<your-api-id>
TG_API_HASH=<your-api-hash>
TG_SESSION_DIR=/app/sessions

# SMTP
SMTP_HOST=smtp.provider.com
SMTP_PORT=587
SMTP_USERNAME=<username>
SMTP_PASSWORD=<password>
SMTP_USE_TLS=True
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=Your App

# Media
MEDIA_STORAGE_PROVIDER=s3
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_S3_BUCKET_NAME=your-bucket
AWS_S3_REGION=us-east-1
```

### Docker Swarm

```bash
# Создайте secrets
echo "<secure-password" | docker secret create postgres_password -
echo "<secure-key" | docker secret create jwt_secret -

# Развёртывание
docker stack deploy -c docker-compose.prod.yml ms_starter
```

### Kubernetes

Создайте манифесты:
- `deployment.yaml` — Deployment для приложения
- `service.yaml` — Service для балансировки
- `configmap.yaml` — ConfigMap для переменных окружения
- `secret.yaml` — Secret для чувствительных данных
- `ingress.yaml` — Ingress для внешнего доступа

---

## Миграции БД

### Alembic конфигурация

```bash
# alembic.ini
sqlalchemy.url = postgresql+asyncpg://user:password@host:5432/dbname
```

### Создание миграции

```bash
# Автогенерация миграции на основе моделей
alembic revision --autogenerate -m "Description of changes"

# Просмотр SQL без применения
alembic upgrade head --sql
```

### Применение миграций

```bash
# Применить все миграции
alembic upgrade head

# Откатить на одну миграцию
alembic downgrade -1

# Откатить к конкретной ревизии
alembic downgrade <revision-id>
```

### Миграции в Docker

```bash
# Запуск миграций в контейнере
docker-compose exec app alembic upgrade head

# Или через отдельный сервис
docker-compose run --rm app alembic upgrade head
```

---

## Мониторинг и логирование

### Health Check

Эндпоинт для проверки здоровья:

```bash
GET /health
Response: {"status": "ok"}
```

**Docker Compose:**

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Логирование

**Уровни логирования:**
- `DEBUG` — детальная отладка
- `INFO` — нормальные события
- `WARNING` — предупреждения
- `ERROR` — ошибки
- `CRITICAL` — критические ошибки

**Настройка уровня:**

```bash
# .env
LOG_LEVEL=INFO
```

### Сбор логов

**Docker:**
```bash
# Просмотр логов
docker-compose logs -f app

# Логирование в файл
docker-compose logs -f app > app.log
```

**Production:**
- Используйте централизованные системы: ELK Stack, Graylog, Splunk
- Настройте алерты на ошибки (Prometheus + Alertmanager)

---

## Чек-лист перед развёртыванием

- [ ] Все пароли изменены на уникальные
- [ ] `DEBUG=False`
- [ ] `CREATE_TABLES_ON_STARTUP=False`
- [ ] Миграции применены
- [ ] Health check настроен
- [ ] Логирование настроено
- [ ] Бэкапы БД настроены
- [ ] Мониторинг настроен
- [ ] Секреты защищены (не в git!)

---

## Ссылки

- [Docker Compose documentation](https://docs.docker.com/compose/)
- [Alembic documentation](https://alembic.sqlalchemy.org/)
- [FastAPI deployment](https://fastapi.tiangolo.com/deployment/)
