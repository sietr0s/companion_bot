"""Manager routes grouped by entity; authentication is applied by the level router."""

from fastapi import APIRouter

from src.base.routers import create_crud_router
from src.modules.memory.dependencies import get_vector_record_service
from src.modules.memory.schemas.api import (
    VectorRecordCreate,
    VectorRecordRead,
    VectorRecordUpdate,
)

router = APIRouter()

router.include_router(
    create_crud_router(
        get_service=get_vector_record_service,
        create_schema=VectorRecordCreate,
        update_schema=VectorRecordUpdate,
        response_schema=VectorRecordRead,
        prefix="/vector-records",
        tags=["Memory"],
        entity_name="VectorRecord",
    )
)
