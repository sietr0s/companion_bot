"""Administrative CRUD services."""

import logging

from src.base.service import BaseService
from src.modules.memory.models import Conversation, Message, SummaryState, VectorRecord
from src.modules.memory.repository import (
    ConversationRepository,
    MessageRepository,
    SummaryStateRepository,
    VectorRecordRepository,
)

logger = logging.getLogger(__name__)


class ConversationService(BaseService[ConversationRepository, Conversation]):
    def __init__(self, repository: ConversationRepository) -> None:
        super().__init__(repository)


class MessageService(BaseService[MessageRepository, Message]):
    def __init__(self, repository: MessageRepository) -> None:
        super().__init__(repository)


class SummaryStateService(BaseService[SummaryStateRepository, SummaryState]):
    def __init__(self, repository: SummaryStateRepository) -> None:
        super().__init__(repository)


class VectorRecordService(BaseService[VectorRecordRepository, VectorRecord]):
    def __init__(self, repository: VectorRecordRepository) -> None:
        super().__init__(repository)
