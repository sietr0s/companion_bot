# Контроль качества в GitHub

На push и pull request выполняются `CI` и `Code quality`. Отчёты не требуют
SonarCloud, внешнего аккаунта или секретов. В каждом запуске Actions доступны
**Summary** с показателями и скачиваемые **Artifacts** с подробными результатами.
Security-аудит также повторяется еженедельно: новые advisory могут появиться без
изменения исходников. Schedule и Dependabot активируются после попадания конфигурации
в default branch; push-проверки работают и в рабочей ветке.

## Что проверяется

| Проверка | Что показывает | Когда блокирует CI |
| --- | --- | --- |
| Ruff + formatter | ошибки Python, стиль, импорты | любое нарушение |
| pytest + Hypothesis | сценарии backend, транзакции, границы модулей, случайные входы | упавший тест |
| coverage.py | строки и ветвления всего `src`, кроме `__init__.py` | падение ниже порогов |
| Vitest + Testing Library | React-компоненты, авторизация, API errors, utilities | упавший тест |
| V8 coverage | весь frontend, включая ещё не покрытые страницы | падение ниже порогов |
| ESLint + TypeScript + Vite | React/TypeScript, форматирование и сборка | ошибка линтера, типов или сборки |
| mypy strict | типы и совместимость контрактов Python | новое замечание или рост повторов |
| Radon CC | цикломатическая сложность функций, методов и вложенных callbacks | новая сложность >10 или ухудшение принятого значения |
| Radon MI | индекс сопровождаемости по файлам | новый индекс <20 или его ухудшение |
| Vulture | потенциально мёртвый код, confidence >=80% | новое замечание |
| jscpd | повторяющиеся блоки Python/TS/TSX от 10 строк и 70 токенов | новый/увеличенный повтор |
| Bandit | потенциально небезопасные конструкции Python | новое замечание любой severity |
| pip-audit | известные уязвимости установленных Python-пакетов | любая известная уязвимость или сбой аудита |
| npm audit | уязвимости runtime и dev-зависимостей | high/critical или сбой аудита |
| actionlint | выражения, ключи workflow и shell-команды Actions | ошибка workflow |
| Dependabot | предложения обновить Python/npm/Actions зависимости | создаёт PR; проверки выполняются в обычном порядке |

HTML покрытия показывает конкретные непройденные строки и ветвления. JSON/XML/LCOV
сохраняются для дальнейшей интеграции с dashboard. Отчёты хранятся 30 дней;
долгосрочное состояние сохраняется в git: policy, baseline и тесты.

## Точка отсчёта и пороги

После расширения измерения backend покрыт на **84,29% строк / 60,56% ветвей**;
комбинированный показатель coverage.py — **80,86%**. Выполняются 364 теста,
в том числе шесть генеративных проверок Hypothesis. В CI они детерминированы,
но перебирают множество входов, а не один зафиксированный пример.

Frontend: **29 тестов**, **12,23% строк / 16,86% ветвей** по всему приложению.
Утилиты API/форматирования покрыты полностью, проверены Markdown и авторизация;
большинство страниц пока имеют нулевое покрытие. Эти страницы намеренно остаются
в знаменателе отчёта. Следующий приоритет — пользовательские сценарии страниц
памяти и управления аккаунтами, затем реальные интеграции.

Пороги в `quality-policy.json` закреплены рядом с фактическими значениями:
backend 80,5% combined / 60% branches; frontend 12% lines / 16,5% branches.
Это минимальные ограничения регрессии, а не целевые показатели качества.
При увеличении покрытия следует повышать их. Не понижать пороги ради зелёного CI.

## Существующий долг не скрывается

`quality-baseline.json` содержит исходные замечания: 110 mypy, 16 сложных функций,
4 low Bandit, 2 Vulture. MI <20 и дубликатов заданного размера на момент внедрения нет.
Замечания Bandit относятся к `assert` защитных проверок шины и `random` для
поведенческого выбора, а не генерации ключей. Vulture отмечает параметры callback,
которые требуются интерфейсом. Они остаются в отчёте для явного review.

Каждая запись содержит инструмент, файл, правило, текст, количество повторов и
значение метрики. Номера строк не участвуют в идентификаторе: добавление комментария
не создаёт ложную регрессию. Для дубликатов используется хеш нормализованного блока.
В отчёте видны все текущие замечания, включая принятые; зелёный ratchet означает
**отсутствие ухудшений**, а не отсутствие code smells или полную типизацию.

При исправлении старого долга удаляйте соответствующие baseline-записи. Обновлять
baseline нужно явно после просмотра diff, а не автоматически при каждом запуске:

```bash
python scripts/quality_report.py --update-baseline
git diff -- quality-baseline.json
```

В CI обновление запрещено. Ошибка/отсутствие анализатора, неполный Bandit scan,
нечитаемый отчёт и нулевое измерение coverage не считаются успешной проверкой.
Это отдельно проверяют тесты quality gates. Не использовать `continue-on-error`
или `|| true` для сокрытия результата анализаторов.

## Уязвимости зависимостей

Инструменты Vite/Vitest и связанные пакеты обновлены до версий без найденных
high/critical advisory; новые версии проверены тестами и production-сборкой.
Остаются 9 moderate npm-замечаний, включая транзитивный minimatch и React Router.
Их исправление требует отдельной совместимой миграции; они видны в security artifact,
даже если security gate проходит. Не применять слепой `npm audit fix --force`.

CPU-wheel PyTorch имеет локальную версию `+cpu`, отсутствующую в advisory-каталоге
PyPI. Поэтому дополнительно проверяется та же публичная версия PyTorch, без её
установки. В Summary явно указано, что это не аудит происхождения CPU-бинарника.
Пропуск другого пакета или невозможность проверить публичную версию ломают gate.
На момент настройки известных Python advisory не найдено.

## Локальный запуск

Python 3.12, Node 24. Для воспроизводимости CI использует
`requirements-ci-constraints.txt` с проверенными версиями runtime/test/quality
пакетов, включая CPU PyTorch. Версии constraints обновляются вместе с прямыми
requirements; после обновления нужно повторить тесты и анализ.

```bash
python -m pip install --upgrade pip setuptools -c requirements-ci-constraints.txt
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch -c requirements-ci-constraints.txt
python -m pip install -r requirements-dev.txt -r requirements-quality.txt -c requirements-ci-constraints.txt
npm ci --prefix frontend --legacy-peer-deps --no-audit --no-fund
python scripts/quality_report.py
python scripts/audit_python.py
```

Backend coverage (с тестовыми env-параметрами из `ci.yml`):

```bash
HYPOTHESIS_PROFILE=ci pytest tests --cov=src --cov-branch \
  --cov-report=json:reports/coverage/backend/coverage.json \
  --cov-report=html:reports/coverage/backend/html
python scripts/coverage_gate.py backend reports/coverage/backend/coverage.json
cd frontend
npm run test:coverage
npm run lint
npm run build
python ../scripts/coverage_gate.py frontend coverage/coverage-summary.json
```

`node_modules`, bytecode, egg-info и результаты сборки исключены из Git.
Для чистой установки достаточно команд выше; отдельная копия frontend не нужна.

## Что отчёты не доказывают

Рабочих E2E с настоящими Telegram/Instagram/LLM-аккаунтами пока нет:
старый неподключённый harness удалён; auth HTTP-сценарии перенесены в интеграционные
тесты. Для внешних E2E потребуются отдельный стенд и тестовые credentials. Анализаторы не доказывают отсутствие
всех ошибок или уязвимостей. Также пока нет браузерных E2E, нагрузочных и mutation
тестов. При расширении системы эти уровни добавляются под конкретные риски,
а не заменяют текущие unit/integration/property проверки.
