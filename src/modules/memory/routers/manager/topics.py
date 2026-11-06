"""Manager routes grouped by entity; authentication is applied by the level router."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.modules.memory.dependencies import (
    get_topic_query_service,
)
from src.modules.memory.schemas.api import (
    MemoryMessageRead,
    VectorTopicDetailRead,
    VectorTopicRead,
)
from src.modules.memory.services.topics import TopicQueryService

router = APIRouter()


@router.get(
    "/conversations/{conversation_id}/topics",
    response_model=list[VectorTopicRead],
)
async def list_conversation_topics(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: TopicQueryService = Depends(get_topic_query_service),
) -> list[VectorTopicRead]:
    return [
        VectorTopicRead.model_validate(topic)
        for topic in await service.list_topics(session, conversation_id)
    ]


@router.get(
    "/conversations/{conversation_id}/topics/{topic_id}",
    response_model=VectorTopicDetailRead,
)
async def get_conversation_topic(
    conversation_id: UUID,
    topic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: TopicQueryService = Depends(get_topic_query_service),
) -> VectorTopicDetailRead:
    history = await service.get_topic(session, conversation_id, topic_id)
    fields = VectorTopicRead.model_validate(history.topic).model_dump()
    fields["message_count"] = len(history.messages)
    return VectorTopicDetailRead(
        **fields,
        messages=[MemoryMessageRead.model_validate(message) for message in history.messages],
    )
