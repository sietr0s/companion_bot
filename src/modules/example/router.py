"""Router для Example модуля."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.core.database import get_async_session
from src.modules.example.schemas import ExampleCreate, ExampleRead, ExampleUpdate
from src.modules.example.service import ExampleService


def get_example_service() -> ExampleService:
    """Фабрика сервиса Example."""
    return ExampleService()


router = APIRouter(prefix="/examples", tags=["Examples"])


@router.post("/", response_model=ExampleRead, status_code=status.HTTP_201_CREATED)
async def create_example(
    data: ExampleCreate,
    session: AsyncSession = Depends(get_async_session),
    service: ExampleService = Depends(get_example_service),
) -> ExampleRead:
    """Создать новый Example."""
    result = await service.create(session, data.model_dump())
    return ExampleRead.model_validate(result)


@router.get("/", response_model=list[ExampleRead])
async def get_examples(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    service: ExampleService = Depends(get_example_service),
) -> list[ExampleRead]:
    """Получить список Example."""
    results = await service.get_all(session, skip, limit)
    return [ExampleRead.model_validate(r) for r in results]


@router.get("/{example_id}", response_model=ExampleRead)
async def get_example(
    example_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    service: ExampleService = Depends(get_example_service),
) -> ExampleRead:
    """Получить Example по ID."""
    result = await service.get_by_id(session, example_id)
    if result is None:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("Example not found")
    return ExampleRead.model_validate(result)


@router.patch("/{example_id}", response_model=ExampleRead)
async def update_example(
    example_id: UUID,
    data: ExampleUpdate,
    session: AsyncSession = Depends(get_async_session),
    service: ExampleService = Depends(get_example_service),
) -> ExampleRead:
    """Обновить Example."""
    result = await service.update(session, example_id, data.model_dump(exclude_unset=True))
    return ExampleRead.model_validate(result)


@router.delete("/{example_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_example(
    example_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    service: ExampleService = Depends(get_example_service),
) -> None:
    """Удалить Example."""
    await service.delete(session, example_id)
