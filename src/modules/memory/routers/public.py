"""Публичные HTTP CRUD-роутеры модуля memory."""

from fastapi import APIRouter

from src.base.routers import create_crud_router
from src.modules.memory.dependencies import (
    get_conversation_service,
    get_message_service,
    get_summary_state_service,
    get_vector_record_service,
)
from src.modules.memory.schemas.public import (
    ConversationCreate,
    ConversationRead,
    ConversationUpdate,
    MemoryMessageCreate,
    MemoryMessageRead,
    MemoryMessageUpdate,
    SummaryStateCreate,
    SummaryStateRead,
    SummaryStateUpdate,
    VectorRecordCreate,
    VectorRecordRead,
    VectorRecordUpdate,
)

router = APIRouter(prefix="/api/v1/public/memory", tags=["Memory"])
router.include_router(
    create_crud_router(
        get_service=get_conversation_service,
        create_schema=ConversationCreate,
        update_schema=ConversationUpdate,
        response_schema=ConversationRead,
        prefix="/conversations",
        tags=["Memory"],
        entity_name="Conversation",
    )
)
router.include_router(
    create_crud_router(
        get_service=get_message_service,
        create_schema=MemoryMessageCreate,
        update_schema=MemoryMessageUpdate,
        response_schema=MemoryMessageRead,
        prefix="/messages",
        tags=["Memory"],
        entity_name="Message",
    )
)
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
