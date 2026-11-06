"""Memory module dependency injection factories."""

from fastapi import Depends

from src.base.service import BaseService
from src.bus import get_producer
from src.bus.interface import MessageProducer
from src.composition.ai import get_memory_intelligence
from src.domain.ai import MemoryIntelligence
from src.modules.memory.models import Conversation, Message, SummaryState, VectorRecord
from src.modules.memory.repository import (
    ConversationRepository,
    MessageRepository,
    SummaryStateRepository,
    VectorRecordRepository,
)
from src.modules.memory.services import MemoryService
from src.modules.memory.services.topics import TopicQueryService


def get_conversation_repository() -> ConversationRepository:
    return ConversationRepository()


def get_message_repository() -> MessageRepository:
    return MessageRepository()


def get_summary_state_repository() -> SummaryStateRepository:
    return SummaryStateRepository()


def get_vector_record_repository() -> VectorRecordRepository:
    return VectorRecordRepository()


def get_topic_query_service(
    vectors: VectorRecordRepository = Depends(get_vector_record_repository),
    messages: MessageRepository = Depends(get_message_repository),
) -> TopicQueryService:
    return TopicQueryService(vectors, messages)


def get_conversation_service(
    repository: ConversationRepository = Depends(get_conversation_repository),
) -> BaseService[ConversationRepository, Conversation]:
    return BaseService(repository)


def get_message_service(
    repository: MessageRepository = Depends(get_message_repository),
) -> BaseService[MessageRepository, Message]:
    return BaseService(repository)


def get_summary_state_service(
    repository: SummaryStateRepository = Depends(get_summary_state_repository),
) -> BaseService[SummaryStateRepository, SummaryState]:
    return BaseService(repository)


def get_vector_record_service(
    repository: VectorRecordRepository = Depends(get_vector_record_repository),
) -> BaseService[VectorRecordRepository, VectorRecord]:
    return BaseService(repository)


def build_memory_service(
    message_bus: MessageProducer | None = None,
    llm: MemoryIntelligence | None = None,
) -> MemoryService:
    return MemoryService(
        conversations=ConversationRepository(),
        messages=MessageRepository(),
        summaries=SummaryStateRepository(),
        vectors=VectorRecordRepository(),
        message_bus=message_bus or get_producer(),
        llm=llm or get_memory_intelligence(),
    )
