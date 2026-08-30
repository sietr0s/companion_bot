"""Публичные CRUD роуты для аккаунтов авторизации."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.base.routers import BaseCRUDRouter
from src.core.database import get_session
from src.modules.auth.dependencies import get_auth_service
from src.modules.auth.models import Auth
from src.modules.auth.schemas_api import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
)
from src.modules.auth.service import AuthService

# Создаём CRUD роутер для аккаунтов
def _get_crud_router() -> BaseCRUDRouter[Auth, AuthService, AccountCreate, AccountUpdate, AccountResponse]:
    """Фабрика CRUD роутера для внедрения зависимости сервиса."""
    return BaseCRUDRouter(
        model=Auth,
        service=None,  # Сервис будет передан через Depends
        create_schema=AccountCreate,
        update_schema=AccountUpdate,
        response_schema=AccountResponse,
        prefix="",
        tags=["Auth Accounts"],
    )

# Глобальный экземпляр роутера (сервис будет инжектиться в каждом запросе)
_crud_router_instance = _get_crud_router()

# Переопределяем методы роутера для правильного получения сервиса из Depends
async def get_list(
    crud_router: BaseCRUDRouter = Depends(lambda: _crud_router_instance),
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(100, ge=1, le=1000, description="Размер страницы"),
    order_by: str | None = Query("-created_at", description="Сортировка"),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Получить список аккаунтов с пагинацией."""
    crud_router.service = auth_service
    return await crud_router.get_list(session=session, page=page, page_size=page_size, order_by=order_by)

async def get_by_id(
    item_id: UUID,
    crud_router: BaseCRUDRouter = Depends(lambda: _crud_router_instance),
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Получить аккаунт по ID."""
    crud_router.service = auth_service
    return await crud_router.get_by_id(item_id=item_id, session=session)

async def create(
    data: AccountCreate,
    crud_router: BaseCRUDRouter = Depends(lambda: _crud_router_instance),
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Создать новый аккаунт."""
    crud_router.service = auth_service
    return await crud_router.create(data=data, session=session)

async def update(
    item_id: UUID,
    data: AccountUpdate,
    crud_router: BaseCRUDRouter = Depends(lambda: _crud_router_instance),
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Обновить аккаунт."""
    crud_router.service = auth_service
    return await crud_router.update(item_id=item_id, data=data, session=session)

async def delete(
    item_id: UUID,
    crud_router: BaseCRUDRouter = Depends(lambda: _crud_router_instance),
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Удалить аккаунт."""
    crud_router.service = auth_service
    return await crud_router.delete(item_id=item_id, session=session)

# Создаём роутер и регистрируем endpoints
router = APIRouter(prefix="/accounts", tags=["Auth Accounts"])
router.add_api_route("/", get_list, methods=["GET"], summary="Get list")
router.add_api_route("/{item_id}", get_by_id, methods=["GET"], summary="Get by ID")
router.add_api_route("/", create, methods=["POST"], summary="Create")
router.add_api_route("/{item_id}", update, methods=["PUT"], summary="Update")
router.add_api_route("/{item_id}", delete, methods=["DELETE"], summary="Delete")
