"""Public memory command API."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.domain.ai import MemoryIntelligence
from src.domain.chat import ChatRef, display_text
from src.modules.memory.domain import NewMessage
from src.modules.memory.exceptions import ConversationNotFoundError
from src.modules.memory.repository import (
    ConversationRepository,
    MessageBatchRepository,
    MessageRepository,
    SummaryStateRepository,
    VectorRecordRepository,
)
from src.modules.memory.schemas.events import (
    BatchProcessedEvent,
    BuildContextCommand,
    ContextBuiltEvent,
    MaintainMemoryCommand,
    MemoryUpdatedEvent,
    ProcessBatchCommand,
    UpdateMemoryCommand,
)
from src.modules.memory.services.context import ContextBuilder
from src.modules.memory.services.maintenance import MemoryMaintenance

logger = logging.getLogger(__name__)


class MemoryService:
    """Public command facade; delegates focused use cases and publishes their results."""

    def __init__(
        self,
        conversations: ConversationRepository,
        messages: MessageRepository,
        summaries: SummaryStateRepository,
        vectors: VectorRecordRepository,
        message_bus: MessageProducer,
        llm: MemoryIntelligence,
        batches: MessageBatchRepository | None = None,
    ) -> None:
        self._conversations = conversations
        self._batches = batches or MessageBatchRepository()
        self._message_bus = message_bus
        self._context = ContextBuilder(conversations, messages, summaries, vectors, llm)
        self._maintenance = MemoryMaintenance(messages, summaries, vectors, llm)

    async def process_batch(
        self, session: AsyncSession, command: ProcessBatchCommand
    ) -> BatchProcessedEvent:
        batch = command.batch
        direction = batch.direction
        conversation = await self._conversations.get_or_create(
            session,
            channel=batch.channel,
            chat_id=batch.chat_id,
            account_id=batch.account_id,
        )

        current_sequence = await self._batches.append_messages(
            session,
            conversation.id,
            direction,
            [
                NewMessage(text=display_text(message), message_type=message.message_type)
                for message in batch.messages
            ],
            batch_id=batch.id,
            touch=True,
        )

        event_batch_processed = BatchProcessedEvent(
            conversation_id=conversation.id,
            channel=batch.channel,
            chat_id=conversation.chat_id,
            account_id=conversation.account_id,
        )
        event_memory_maintain = MaintainMemoryCommand(
            conversation_id=conversation.id,
            channel=batch.channel,
            chat_id=conversation.chat_id,
            account_id=conversation.account_id,
            current_sequence=current_sequence,
        )
        await self._message_bus.publish(
            BusTopics.MEMORY_BATCH_PROCESSED, event_batch_processed.model_dump(mode="json")
        )
        await self._message_bus.publish(
            BusTopics.MEMORY_MAINTAIN, event_memory_maintain.model_dump(mode="json")
        )
        return event_batch_processed

    async def update_memory(
        self, session: AsyncSession, command: UpdateMemoryCommand
    ) -> MemoryUpdatedEvent:
        conversation = await self._conversations.get_state(session, command.conversation_id)
        if not conversation:
            raise ConversationNotFoundError(f"Conversation {command.conversation_id} not found")

        conversation_id = conversation.id
        chat_id = conversation.chat_id
        messages_saved = 0
        summary_updated = False
        if command.delivery_status == "delivered" and command.outgoing_messages:
            current_sequence = await self._batches.append_messages(
                session,
                conversation_id,
                "outgoing",
                [
                    NewMessage(
                        text=text,
                        message_type="voice" if command.message_type == "voice" else "text",
                    )
                    for text in command.outgoing_messages
                ],
            )
            messages_saved = len(command.outgoing_messages)
        event = MemoryUpdatedEvent(
            conversation_id=conversation_id,
            channel=command.channel,
            chat_id=chat_id,
            account_id=conversation.account_id,
            messages_count=messages_saved,
            summary_updated=summary_updated,
        )
        await self._message_bus.publish(BusTopics.MEMORY_UPDATED, event.model_dump(mode="json"))
        if messages_saved:
            await self._message_bus.publish(
                BusTopics.MEMORY_MAINTAIN,
                MaintainMemoryCommand(
                    conversation_id=conversation_id,
                    channel=command.channel,
                    chat_id=chat_id,
                    account_id=conversation.account_id,
                    current_sequence=current_sequence,
                ).model_dump(mode="json"),
            )
        return event

    async def build_context(
        self, session: AsyncSession, command: BuildContextCommand
    ) -> ContextBuiltEvent:
        chat = ChatRef(
            channel=command.channel,
            chat_id=command.chat_id,
            account_id=command.account_id,
            conversation_id=command.conversation_id,
        )
        context = await self._context.build_context(session, chat, command.last_n_messages)
        event = ContextBuiltEvent(
            **chat.model_dump(), **context.model_dump(), retrieved_count=len(context.retrieved)
        )
        await self._message_bus.publish(
            BusTopics.MEMORY_CONTEXT_BUILT, event.model_dump(mode="json")
        )
        return event

    async def maintain_memory(self, session: AsyncSession, command: MaintainMemoryCommand) -> None:
        await self._maintenance.maintain_memory(
            session, command.conversation_id, command.current_sequence
        )
