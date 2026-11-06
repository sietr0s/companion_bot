"""Manager routes grouped by entity; authentication is applied by the level router."""

from fastapi import APIRouter

from src.base.routers import create_crud_router
from src.modules.memory.dependencies import get_summary_state_service
from src.modules.memory.schemas.api import (
    SummaryStateCreate,
    SummaryStateRead,
    SummaryStateUpdate,
)

router = APIRouter()

router.include_router(
    create_crud_router(
        get_service=get_summary_state_service,
        create_schema=SummaryStateCreate,
        update_schema=SummaryStateUpdate,
        response_schema=SummaryStateRead,
        prefix="/summary-states",
        tags=["Memory"],
        entity_name="SummaryState",
    )
)
