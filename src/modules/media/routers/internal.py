"""
Внутренние роуты модуля media.

Доступны только внутри кластера (network-level).
Без JWT-авторизации — доступ ограничивается
Docker network / k8s NetworkPolicy.
Не проверяют is_public — отдают любой файл по ID.
"""

import uuid

from fastapi import APIRouter, Depends, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import parse_filters
from src.base.schemas import PaginatedResponse
from src.core.dependencies import get_db_session
from src.core.internal_auth import require_internal_service_key
from src.modules.media.dependencies import get_media_service
from src.modules.media.schemas.media import FileRead, FileUploadResponse
from src.modules.media.service import MediaService

router = APIRouter(
    prefix="/internal/media",
    tags=["Internal"],
    dependencies=[Depends(require_internal_service_key)],
)

FILTER_FIELDS = {
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
    summary="[Internal] Список всех файлов",
)
async def list_files_internal(
    filters: list[str] = Query(default_factory=list, description="field+operator+value"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    order_by: str = Query(default="-created_at", description="Поле сортировки; '-' = DESC"),
    session: AsyncSession = Depends(get_db_session),
    service: MediaService = Depends(get_media_service),
) -> PaginatedResponse:
    """Получить список всех файлов с фильтрацией и пагинацией (internal)."""
    parsed = parse_filters(filters, allowed_fields=FILTER_FIELDS)
    skip = (page - 1) * limit
    files, total = await service.get_user_files(session, skip, limit, parsed, order_by)
    return PaginatedResponse.from_list(files, total, page=page, page_size=limit)


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Internal] Загрузить файл",
)
async def upload_file(
    file: UploadFile,
    is_public: bool = Form(default=False),
    session: AsyncSession = Depends(get_db_session),
    service: MediaService = Depends(get_media_service),
) -> FileUploadResponse:
    """Загрузить файл (без JWT, network-level доступ)."""
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
    summary="[Internal] Метаданные файла",
)
async def get_file(
    file_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: MediaService = Depends(get_media_service),
) -> FileRead:
    """Метаданные любого файла (включая приватные)."""
    return await service.get(session, file_id)


@router.get(
    "/{file_id}/download",
    summary="[Internal] Скачать файл",
)
async def download_file(
    file_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: MediaService = Depends(get_media_service),
):
    """Скачать любой файл (потоком, включая приватные)."""
    stored_file, stream = await service.download_stream(session, file_id)
    return StreamingResponse(
        stream,
        media_type=stored_file.content_type,
        headers={"Content-Disposition": f'attachment; filename="{stored_file.filename}"'},
    )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Internal] Удалить файл",
)
async def delete_file(
    file_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: MediaService = Depends(get_media_service),
) -> None:
    """Удалить файл (без JWT)."""
    await service.delete(session, file_id)
