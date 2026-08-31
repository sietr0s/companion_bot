"""Batching module CRUD routers."""

from src.base.routers import create_crud_router
from src.modules.batching.dependencies import get_batch_message_service, get_batching_service
from src.modules.batching.schemas.public import (
    BatchCreate,
    BatchMessageCreate,
    BatchMessageResponse,
    BatchMessageUpdate,
    BatchResponse,
    BatchUpdate,
)

router = create_crud_router(
    get_service=get_batching_service,
    create_schema=BatchCreate,
    update_schema=BatchUpdate,
    response_schema=BatchResponse,
    prefix="/api/v1/public/batches",
    tags=["Batching"],
    entity_name="Batch",
)

messages_router = create_crud_router(
    get_service=get_batch_message_service,
    create_schema=BatchMessageCreate,
    update_schema=BatchMessageUpdate,
    response_schema=BatchMessageResponse,
    prefix="/api/v1/public/batch-messages",
    tags=["Batching"],
    entity_name="BatchMessage",
)
