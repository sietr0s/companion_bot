"""Публичные HTTP CRUD-роутеры модуля memory."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.routers import create_crud_router
from src.core.dependencies import get_current_admin, get_db_session
from src.modules.memory.dependencies import (
    get_conversation_service,
    get_memory_service,
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
    VectorTopicDetailRead,
    VectorTopicRead,
)
from src.modules.memory.service import MemoryService

router = APIRouter(
    prefix="/api/v1/public/memory",
    tags=["Memory"],
    dependencies=[Depends(get_current_admin)],
)
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


@router.get(
    "/conversations/{conversation_id}/topics",
    response_model=list[VectorTopicRead],
)
async def list_conversation_topics(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: MemoryService = Depends(get_memory_service),
) -> list[VectorTopicRead]:
    return await service.list_topics(session, conversation_id)


@router.get(
    "/conversations/{conversation_id}/topics/{topic_id}",
    response_model=VectorTopicDetailRead,
)
async def get_conversation_topic(
    conversation_id: UUID,
    topic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: MemoryService = Depends(get_memory_service),
) -> VectorTopicDetailRead:
    return await service.get_topic(session, conversation_id, topic_id)
