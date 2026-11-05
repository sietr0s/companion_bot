"""Memory module dependency injection factories."""

from fastapi import Depends

from src.bus import get_producer
from src.bus.interface import MessageProducer
from src.composition.ai import get_memory_intelligence
from src.domain.ai import MemoryIntelligence
from src.modules.memory.repository import (
    ConversationRepository,
    MessageRepository,
    SummaryStateRepository,
    VectorRecordRepository,
)
from src.modules.memory.service import (
    ConversationService,
    MemoryService,
    MessageService,
    SummaryStateService,
    VectorRecordService,
)
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
) -> ConversationService:
    return ConversationService(repository)


def get_message_service(
    repository: MessageRepository = Depends(get_message_repository),
) -> MessageService:
    return MessageService(repository)


def get_summary_state_service(
    repository: SummaryStateRepository = Depends(get_summary_state_repository),
) -> SummaryStateService:
    return SummaryStateService(repository)


def get_vector_record_service(
    repository: VectorRecordRepository = Depends(get_vector_record_repository),
) -> VectorRecordService:
    return VectorRecordService(repository)


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


def get_memory_service(
    conversations: ConversationRepository = Depends(get_conversation_repository),
    messages: MessageRepository = Depends(get_message_repository),
    summaries: SummaryStateRepository = Depends(get_summary_state_repository),
    vectors: VectorRecordRepository = Depends(get_vector_record_repository),
    llm: MemoryIntelligence = Depends(get_memory_intelligence),
) -> MemoryService:
    return MemoryService(
        conversations=conversations,
        messages=messages,
        summaries=summaries,
        vectors=vectors,
        message_bus=get_producer(),
        llm=llm,
    )
