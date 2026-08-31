"""Memory module HTTP CRUD routers."""

from fastapi import APIRouter

from src.base.routers import create_crud_router
from src.modules.memory.dependencies import (
    get_conversation_service,
    get_message_service,
    get_summary_state_service,
    get_vector_record_service,
)
from src.modules.memory.schemas.public import (
    ConversationCreateRequest,
    ConversationResponse,
    ConversationUpdateRequest,
    MessageCreateRequest,
    MessageResponse,
    MessageUpdateRequest,
    SummaryStateCreateRequest,
    SummaryStateResponse,
    SummaryStateUpdateRequest,
    VectorRecordCreateRequest,
    VectorRecordResponse,
    VectorRecordUpdateRequest,
)

router = APIRouter(prefix="/memory", tags=["memory"])
router.include_router(
    create_crud_router(
        get_service=get_conversation_service,
        create_schema=ConversationCreateRequest,
        update_schema=ConversationUpdateRequest,
        response_schema=ConversationResponse,
        prefix="/conversations",
        tags=["memory"],
        entity_name="Conversation",
    )
)
router.include_router(
    create_crud_router(
        get_service=get_message_service,
        create_schema=MessageCreateRequest,
        update_schema=MessageUpdateRequest,
        response_schema=MessageResponse,
        prefix="/messages",
        tags=["memory"],
        entity_name="Message",
    )
)
router.include_router(
    create_crud_router(
        get_service=get_summary_state_service,
        create_schema=SummaryStateCreateRequest,
        update_schema=SummaryStateUpdateRequest,
        response_schema=SummaryStateResponse,
        prefix="/summary-states",
        tags=["memory"],
        entity_name="SummaryState",
    )
)
router.include_router(
    create_crud_router(
        get_service=get_vector_record_service,
        create_schema=VectorRecordCreateRequest,
        update_schema=VectorRecordUpdateRequest,
        response_schema=VectorRecordResponse,
        prefix="/vector-records",
        tags=["memory"],
        entity_name="VectorRecord",
    )
)
