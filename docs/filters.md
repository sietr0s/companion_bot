# Универсальная фильтрация (Filters)

В проекте реализована универсальная система фильтрации для репозиториев и внутренних роутов. Фильтрация позволяет динамически строить SQL-запросы на основе URL-параметров.

---

## Содержание

1. [Базовое использование](#базовое-использование)
2. [Операторы](#операторы)
3. [Примеры](#примеры)
4. [Использование в роутерах](#использование-в-роутерах)
5. [Использование в репозиториях](#использование-в-репозиториях)
6. [Комбинирование фильтров](#комбинирование-фильтров)

---

## Базовое использование

Формат параметра фильтра: `field+operator+value`

**Пример URL:**
```
GET /internal/users/?filters=auth_id+eq+550e8400-e29b-41d4-a716-446655440000
```

**Парсинг фильтров:**
```python
from src.base.filters import parse_filters, apply_filters
from sqlalchemy import select

# Парсинг строковых фильтров из URL
filters = parse_filters([
    "auth_id+eq+550e8400-e29b-41d4-a716-446655440000",
    "email+eq+test@example.com"
])

# Применение к SQLAlchemy запросу
stmt = select(MyModel)
stmt = apply_filters(stmt, MyModel, filters)
```

---

## Операторы

| Оператор | Описание | Пример |
|----------|----------|--------|
| `eq` | Равно | `status+eq+active` |
| `ne` | Не равно | `role+ne+admin` |
| `gt` | Больше | `age+gt+18` |
| `ge` | Больше или равно | `created_at+ge+2024-01-01` |
| `lt` | Меньше | `price+lt+1000` |
| `le` | Меньше или равно | `rating+le+5` |
| `like` | LIKE (регистрозависимый) | `name+like+John%` |
| `ilike` | ILIKE (регистронезависимый) | `email+ilike+%@gmail.com` |
| `in` | IN (список значений) | `status+in+active,pending` |

---

## Примеры

### Фильтрация по UUID
```
GET /internal/users/?filters=auth_id+eq+550e8400-e29b-41d4-a716-446655440000
```

### Фильтрация по строке
```
GET /internal/users/?filters=email+eq+test@example.com
```

### Фильтрация по числу
```
GET /internal/offers/?filters=salary_from+gt+100000
```

### Фильтрация по дате
```
GET /internal/logs/?filters=created_at+ge+2024-01-01
```

### Фильтрация с LIKE
```
GET /internal/users/?filters=first_name+like+Alex%
```

### Фильтрация с IN
```
GET /internal/offers/?filters=status+in+active,pending,closed
```

### Комбинированные фильтры
```
GET /internal/offers/?filters=salary_from+gt+100000&filters=location+eq+Moscow
```

---

## Использование в роутерах

### Внутренние роуты (/internal/)

```python
from fastapi import APIRouter, Query
from sqlalchemy import select
from src.base.filters import parse_filters, apply_filters
from src.modules.users.models import User

router = APIRouter()

@router.get("/")
async def get_users(
    filters: list[str] = Query(default=[]),
    skip: int = 0,
    limit: int = 100,
):
    """
    Получить список пользователей с фильтрацией.
    
    Пример:
    GET /internal/users/?filters=auth_id+eq+550e8400&filters=email+eq+test@test.com
    """
    parsed_filters = parse_filters(filters)
    
    stmt = select(User)
    stmt = apply_filters(stmt, User, parsed_filters)
    stmt = stmt.offset(skip).limit(limit)
    
    result = await session.execute(stmt)
    return result.scalars().all()
```

---

## Использование в репозиториях

### Кастомные методы с фильтрацией

```python
from src.base.repository import BaseRepository
from src.base.filters import parse_filters, apply_filters
from src.modules.users.models import User

class UserRepository(BaseRepository[User]):
    """Репозиторий профилей пользователей."""

    async def get_list(
        self,
        session: AsyncSession,
        filters: list[str] | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        """
        Получить список пользователей с фильтрацией.
        
        Args:
            session: SQLAlchemy async session
            filters: Список строк фильтрации (например, ["auth_id+eq+..."])
            skip: Пропуск первых N записей
            limit: Максимальное количество записей
        
        Returns:
            Список пользователей
        """
        from sqlalchemy import select
        
        stmt = select(User)
        
        if filters:
            parsed = parse_filters(filters)
            stmt = apply_filters(stmt, User, parsed)
        
        stmt = stmt.offset(skip).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()
```

---

## Комбинирование фильтров

### Множественные фильтры по одному полю

```
GET /internal/offers/?filters=salary_from+gt+100000&filters=salary_from+lt+500000
```

### Фильтры по разным полям

```
GET /internal/offers/?filters=location+eq+Moscow&filters=salary_from+gt+100000&filters=status+eq+active
```

### Фильтры с пагинацией

```
GET /internal/offers/?filters=status+eq+active&skip=0&limit=20
```

---

## Обработка ошибок

### Некорректный формат фильтра

Если формат фильтра не соответствует `field+operator+value`, будет выброшено исключение:

```python
from src.base.filters import parse_filters

try:
    filters = parse_filters(["invalid_format"])
except ValueError as e:
    # Обработка ошибки
    pass
```

### Несуществующее поле

Если поле не существует в модели, SQLAlchemy выбросит исключение при выполнении запроса.

### Некорректный тип значения

Фильтрация автоматически приводит типы:
- UUID: строка в формате UUID
- int: целые числа
- float: дробные числа
- str: строки
- datetime: ISO 8601 формат (YYYY-MM-DD)

---

## Расширение: кастомные операторы

Для добавления собственных операторов расширьте `FilterOperator`:

```python
from src.base.filters import FilterOperator

# Добавить новый оператор
class CustomOperator(FilterOperator):
    CONTAINS = "contains"  # Содержит значение
    OVERLAPS = "overlaps"  # Пересекается со списком
```

---

## Ссылки

- [SQLAlchemy Core](https://docs.sqlalchemy.org/en/20/core/)
- [FastAPI Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/)
