"""Memory module dependency injection factories."""

from fastapi import Depends

from src.bus import get_producer
from src.modules.llm.dependencies import get_llm_service
from src.modules.llm.service import LLMService
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


def get_conversation_repository() -> ConversationRepository:
    return ConversationRepository()


def get_message_repository() -> MessageRepository:
    return MessageRepository()


def get_summary_state_repository() -> SummaryStateRepository:
    return SummaryStateRepository()


def get_vector_record_repository() -> VectorRecordRepository:
    return VectorRecordRepository()


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


def get_memory_service(
    conversations: ConversationRepository = Depends(get_conversation_repository),
    messages: MessageRepository = Depends(get_message_repository),
    summaries: SummaryStateRepository = Depends(get_summary_state_repository),
    vectors: VectorRecordRepository = Depends(get_vector_record_repository),
    llm: LLMService = Depends(get_llm_service),
) -> MemoryService:
    return MemoryService(
        conversations=conversations,
        messages=messages,
        summaries=summaries,
        vectors=vectors,
        message_bus=get_producer(),
        llm=llm,
    )
