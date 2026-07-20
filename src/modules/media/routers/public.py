"""
Публичные роуты модуля media.

GET /media/{id} и /media/{id}/download — доступны без JWT
только для is_public=True файлов.
POST /media/upload и DELETE /media/{id} — требуют JWT.
"""

import uuid

from fastapi import APIRouter, Depends, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import parse_filters
from src.base.schemas import PaginatedResponse
from src.core.dependencies import get_current_admin, get_current_user, get_db_session
from src.core.exceptions import NotFoundError
from src.modules.media.dependencies import get_media_service
from src.modules.media.schemas.media import FileRead, FileUploadResponse
from src.modules.media.service import MediaService

router = APIRouter(prefix="/api/v1/public/media", tags=["Media"])

ADMIN_FILTER_FIELDS = {
    "id",
    "filename",
    "content_type",
    "size_bytes",
    "is_public",
    "created_at",
    "updated_at",
}


@router.get(
    "/",
    response_model=PaginatedResponse[FileRead],
    summary="Получить файлы для администратора",
)
async def list_files_admin(
    filters: list[str] = Query(default_factory=list, description="field+operator+value"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    order_by: str = Query(default="-created_at", description="Поле сортировки; '-' = DESC"),
    _admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: MediaService = Depends(get_media_service),
) -> PaginatedResponse[FileRead]:
    """Вернуть список файлов авторизованному администратору."""
    parsed = parse_filters(filters, allowed_fields=ADMIN_FILTER_FIELDS)
    files, total = await service.get_user_files(
        session,
        skip=(page - 1) * limit,
        limit=limit,
        filters=parsed,
        order_by=order_by,
    )
    return PaginatedResponse.from_list(files, total, page=page, page_size=limit)


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузить файл",
)
async def upload_file(
    file: UploadFile,
    is_public: bool = Form(default=False),
    session: AsyncSession = Depends(get_db_session),
    _user_id: uuid.UUID = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
) -> FileUploadResponse:
    """Загрузить файл (требует JWT)."""
    data = await file.read()
    stored_file = await service.upload(
        session=session,
        filename=file.filename or "unnamed",
        data=data,
        content_type=file.content_type or "application/octet-stream",
        is_public=is_public,
    )
    return stored_file


@router.get(
    "/{file_id}",
    response_model=FileRead,
    summary="Метаданные файла",
)
async def get_file(
    file_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: MediaService = Depends(get_media_service),
) -> FileRead:
    """
    Получить метаданные файла.

    Публичные файлы (is_public=True) доступны без авторизации.
    Приватные файлы возвращают 404.
    """
    stored_file = await service.get(session, file_id)
    if not stored_file.is_public:
        raise NotFoundError(detail="Файл не найден")
    return stored_file


@router.get(
    "/{file_id}/download",
    summary="Скачать файл",
)
async def download_file(
    file_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: MediaService = Depends(get_media_service),
):
    """
    Скачать файл (потоком).

    Публичные файлы (is_public=True) доступны без авторизации.
    Приватные файлы возвращают 404.
    """
    stored_file, stream = await service.download_stream(session, file_id)
    if not stored_file.is_public:
        raise NotFoundError(detail="Файл не найден")

    return StreamingResponse(
        stream,
        media_type=stored_file.content_type,
        headers={"Content-Disposition": f'attachment; filename="{stored_file.filename}"'},
    )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить файл",
)
async def delete_file(
    file_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    _user_id: uuid.UUID = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
) -> None:
    """Удалить файл (требует JWT)."""
    await service.delete(session, file_id)
