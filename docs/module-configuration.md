# Конфигурация модулей

Для каждого из 11 модулей реализованы `config/`, собственная таблица
`<module>_configuration`, единые базовые классы и автоматически собранный manager API.
Ниже примеры для Batching; остальные модули используют тот же контракт.
Имена URL: auth, users, llm, telegram, instagram, stt, tts, memory, behavior,
batching, orchestrator.
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
router в `routers/manager/configuration.py` и миграцию таблицы. Его `main.py` объявляет ORM-модели и lifecycle в `ModuleDefinition`, модуль
добавляется в `composition/modules.py`. Хост загружает снимки до подготовки
бизнес-сервисов; текущие снимки неизменяемы (ADR 0005).
Секреты и bootstrap-параметры в такие HTTP-схемы включать нельзя.

Frontend на этом этапе не изменён; контракт доступен в `/openapi.json` backend.

Проверки включают config API всех модулей, изоляцию таблиц/revision,
safe-mode startup/API/restart без сети, ошибки startup и очистку ресурсов. Полной истории изменений пока нет, сохраняются
последняя revision, updated_at и updated_by.

Конфигурационные endpoints находятся в обычном `module/routers/manager/configuration.py`.
Пакет `config/` не содержит роутеров. `main` подключает только `module.routers.router`;
сборка HTTP-маршрутов принадлежит самому модулю.

Префиксы собираются по уровням: `routers/__init__.py` → `manager/__init__.py`
(уровень доступа и пространство модуля) → `manager/configuration.py`
(только `/configuration`). В фабрику не передаётся полный API URL.

Статические `/configuration` подключаются до CRUD `/{id}`, чтобы не попадать
в разбор идентификатора. Сборка и отдельный запуск — [ADR 0005](adr/0005-module-runtime-and-entrypoints.md).
