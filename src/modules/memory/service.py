"""Memory module business logic service."""


from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.memory.exceptions import ConversationNotFoundError
from src.modules.memory.repository import MemoryRepository
from src.modules.memory.schemas_bus import (
    BatchProcessedEvent,
    BuildContextCommand,
    ContextBuiltEvent,
    MemoryUpdatedEvent,
    ProcessBatchCommand,
    UpdateMemoryCommand,
)


class MemoryService:
    """Service for memory-related business logic."""

    def __init__(
        self,
        repository: MemoryRepository,
        message_bus: MessageProducer,
    ):
        self._repo = repository
        self._message_bus = message_bus

    async def process_batch(
        self,
        command: ProcessBatchCommand,
    ) -> BatchProcessedEvent:
        """Process a batch of messages and save to conversation."""
        # Get or create conversation
        conversation = await self._repo.get_or_create_conversation(
            telegram_chat_id=command.telegram_chat_id,
            user_id=command.conversation_id,  # In real app, this would be different
        )

        # Prepare messages data
        current_sequence = conversation.last_sequence_number
        messages_data = []
        sequence_numbers = []

        for _, text in enumerate(command.messages):
            current_sequence += 1
            messages_data.append({
                "text": text,
                "direction": command.direction,
                "message_type": command.message_type,
                "sequence_number": current_sequence,
                "batch_id": command.batch_id,
            })
            sequence_numbers.append(current_sequence)

        # Save messages
        await self._repo.save_messages(conversation.id, messages_data)

        # Update conversation activity
        await self._repo.update_conversation_activity(
            conversation.id,
            current_sequence,
        )

        # Publish event
        event = BatchProcessedEvent(
            conversation_id=conversation.id,
            telegram_chat_id=conversation.telegram_chat_id,
            sequence_numbers=sequence_numbers,
        )

        await self._message_bus.publish(
            topic=BusTopics.MEMORY_OUT,
            action="batch_processed",
            payload=event.model_dump(),
        )

        return event

    async def build_context(
        self,
        command: BuildContextCommand,
    ) -> ContextBuiltEvent:
        """Build context for LLM from conversation history."""
        # Get last messages
        messages = await self._repo.get_last_messages(
            conversation_id=command.conversation_id,
            limit=command.last_n_messages,
        )

        # Get summary state
        summary_state = await self._repo.get_summary_state(command.conversation_id)
        summary = summary_state.current_summary if summary_state else None

        # Build context (simplified - in real app would use RAG)
        context_parts = []
        if summary:
            context_parts.append(f"Summary: {summary}")

        for msg in messages:
            direction_label = "User" if msg.direction == "incoming" else "Assistant"
            context_parts.append(f"{direction_label}: {msg.text}")

        context = "\n".join(context_parts)

        # Publish event
        event = ContextBuiltEvent(
            conversation_id=command.conversation_id,
            telegram_chat_id=command.telegram_chat_id,
            context=context,
            retrieved_count=len(messages),
        )

        await self._message_bus.publish(
            topic=BusTopics.MEMORY_OUT,
            action="context_built",
            payload=event.model_dump(),
        )

        return event

    async def update_memory(
        self,
        command: UpdateMemoryCommand,
    ) -> MemoryUpdatedEvent:
        """Update memory after message delivery."""
        # Get conversation
        conversation = await self._repo.get_conversation_by_id(
            command.conversation_id
        )
        if not conversation:
            raise ConversationNotFoundError(
                f"Conversation {command.conversation_id} not found"
            )

        # Save outgoing messages if delivered
        messages_saved = 0
        if command.delivery_status == "delivered":
            current_sequence = conversation.last_sequence_number
            messages_data = []

            for text in command.outgoing_messages:
                current_sequence += 1
                messages_data.append({
                    "text": text,
                    "direction": "outgoing",
                    "message_type": "text",
                    "sequence_number": current_sequence,
                })
                messages_saved += 1

            if messages_data:
                await self._repo.save_messages(conversation.id, messages_data)
                await self._repo.update_conversation_activity(
                    conversation.id,
                    current_sequence,
                )

        # Check if summarization is needed (threshold: 100 messages)
        message_count = await self._repo.get_message_count(conversation.id)
        summary_updated = False

        if message_count >= 100:
            # In real app, would call LLM to summarize
            # For now, just mark as needing update
            summary_updated = True

        # Publish event
        event = MemoryUpdatedEvent(
            conversation_id=command.conversation_id,
            telegram_chat_id=conversation.telegram_chat_id,
            messages_count=messages_saved,
            summary_updated=summary_updated,
        )

        await self._message_bus.publish(
            topic=BusTopics.MEMORY_OUT,
            action="memory_updated",
            payload=event.model_dump(),
        )

        return event
