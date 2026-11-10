# Конфигурация модулей: backend-пилот Batching

Реализованы общие классы, отдельная таблица `batching_configuration`, модульный
пакет `src/modules/batching/config/` и автоматически собранный manager-router.
Полная архитектура и ограничения — [ADR 0004](adr/0004-module-configuration.md).

После обновления backend выполнить `alembic upgrade head`. Safe mode создаёт
свою SQLite-схему при startup. Для уже существующей несовместимой dev-базы следует
выбрать новый SAFE_MODE_DATABASE_PATH, сохранив прежний файл.

Все endpoints требуют `Authorization: Bearer <admin access token>`:

| Метод | Путь | Назначение |
| --- | --- | --- |
| GET | `/api/v1/public/batching/configuration` | Значения, источники, JSON Schema и revision |
| PATCH | `/api/v1/public/batching/configuration` | Атомарное изменение разрешённых полей |
| POST | `/api/v1/public/batching/configuration/reset` | Сброс выбранных переопределений |

Изменение:

```json
{"revision": 0, "values": {"BATCH_MAX_SIZE": 5, "BATCH_IDLE_SECONDS": 1.5}}
```

Сброс к ENV/дефолту:

```json
{"revision": 1, "fields": ["BATCH_MAX_SIZE"]}
```

Использовать актуальную revision из GET/последнего ответа. Ошибка 409 означает,
что запись уже изменил другой запрос: нужно перечитать и согласовать новые правки.
Ошибка 422 не сохраняет ни одного поля. `null` не означает reset и для текущих двух
полей недопустим. BATCH_MAX_SIZE >=1, BATCH_IDLE_SECONDS >0; нечисловые/нефинитные
значения, которые не проходят проверку схемы, отклоняются.

`values` содержит результат БД → ENV → дефолт для следующего запуска;
`apply_mode="restart"` описывает способ применения, а не факт ожидающего rollout.
`sources` показывает `database`, `environment` или `default`. `field_schema` описывает
поля для будущего UI. API всегда напоминает о restart и не утверждает, что все worker
уже приняли конфигурацию. ENV-файлы и окружение процесса при сохранении не меняются.

Новый модуль добавляет свою schema/model/repository/service, фабрику dependencies,
router в `config/routes/manager.py` и миграцию таблицы. Его модель регистрируется в
composition/models.py, загрузка снимка выполняется в composition до создания его
бизнес-сервисов. Сервис получает config явно; общего глобального mutable settings нет.
Секреты и bootstrap-параметры в такие HTTP-схемы включать нельзя.

Frontend на этом этапе не изменён; контракт доступен в `/openapi.json` backend.

Проверки пилота: 396 backend-тестов; safe-mode startup/API/restart без сети;
SQLite migration upgrade/downgrade; отдельный PostgreSQL-тест гонки двух редакторов
в изолированной временной схеме. Полной истории изменений пока нет, сохраняются
последняя revision, updated_at и updated_by.
