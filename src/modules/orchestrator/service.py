"""Orchestrator module business logic service."""

from datetime import datetime
from uuid import UUID, uuid4

from src.bus.interface import MessageConsumer, MessageProducer
from src.modules.orchestrator.schemas_bus import (
    AddMessageToBatchCommand,
    BuildContextCommand,
    GenerateReplyCommand,
    OrchestratorState,
    ProcessBatchCommand,
    SendMessageCommand,
    UpdateMemoryCommand,
)


class OrchestratorService:
    """Service for orchestrating message flow between modules."""

    def __init__(
        self,
        message_consumer: MessageConsumer,
        message_producer: MessageProducer,
    ):
        self._consumer = message_consumer
        self._producer = message_producer
        self._states: dict[UUID, OrchestratorState] = {}

    def register_all_handlers(self) -> None:
        """Register all event handlers for orchestrator."""
        # Subscribe to all .out topics
        self._subscribe_to_telegram_clients()
        self._subscribe_to_batching()
        self._subscribe_to_users()
        self._subscribe_to_memory()
        self._subscribe_to_llm()

    def _subscribe_to_telegram_clients(self) -> None:
        """Subscribe to telegram_clients.out events."""

        async def on_message_received(payload: dict) -> dict:
            """Handle incoming message received event."""
            correlation_id = UUID(payload.get("correlation_id", str(uuid4())))
            telegram_chat_id = payload.get("chat_id")
            message_text = payload.get("text")

            # Store state
            state = OrchestratorState(
                correlation_id=correlation_id,
                current_message=message_text,
            )
            self._states[correlation_id] = state

            # Publish to batching
            command = AddMessageToBatchCommand(
                telegram_chat_id=telegram_chat_id,
                message_text=message_text,
            )
            await self._producer.publish(
                topic="batching.in",
                action="add_message",
                payload=command.model_dump(),
                correlation_id=str(correlation_id),
            )
            return {"status": "forwarded_to_batching"}

        self._consumer.subscribe(
            topic="telegram_clients.out",
            action="message_received",
            schema=dict,  # Will be typed in final implementation
            handler=on_message_received,
        )

        async def on_message_sent(payload: dict) -> dict:
            """Handle message sent event."""
            correlation_id = UUID(payload.get("correlation_id"))
            conversation_id = UUID(payload.get("conversation_id"))
            telegram_chat_id = payload.get("chat_id")
            messages = payload.get("messages", [])

            # Update state
            state = self._states.get(correlation_id)
            if state:
                state.reply_messages = messages
                state.updated_at = datetime.utcnow()

            # Publish to memory for update
            command = UpdateMemoryCommand(
                conversation_id=conversation_id,
                telegram_chat_id=telegram_chat_id,
                outgoing_messages=messages,
                delivery_status="delivered",
            )
            await self._producer.publish(
                topic="memory.in",
                action="update_memory",
                payload=command.model_dump(),
                correlation_id=str(correlation_id),
            )
            return {"status": "memory_updated"}

        self._consumer.subscribe(
            topic="telegram_clients.out",
            action="message_sent",
            schema=dict,
            handler=on_message_sent,
        )

    def _subscribe_to_batching(self) -> None:
        """Subscribe to batching.out events."""

        async def on_batch_ready(payload: dict) -> dict:
            """Handle batch ready event."""
            correlation_id = UUID(payload.get("correlation_id", str(uuid4())))
            conversation_id = UUID(payload.get("conversation_id", str(uuid4())))
            telegram_chat_id = payload.get("telegram_chat_id")
            messages = payload.get("messages", [])

            # Update state
            state = self._states.get(correlation_id) or OrchestratorState(
                correlation_id=correlation_id,
            )
            state.current_batch = messages
            state.updated_at = datetime.utcnow()
            self._states[correlation_id] = state

            # First get/create user
            # Then process batch in memory
            command = ProcessBatchCommand(
                conversation_id=conversation_id,
                telegram_chat_id=telegram_chat_id,
                messages=messages,
            )
            await self._producer.publish(
                topic="memory.in",
                action="process_batch",
                payload=command.model_dump(),
                correlation_id=str(correlation_id),
            )
            return {"status": "batch_processing_started"}

        self._consumer.subscribe(
            topic="batching.out",
            action="batch_ready",
            schema=dict,
            handler=on_batch_ready,
        )

    def _subscribe_to_users(self) -> None:
        """Subscribe to users.out events."""
        # In full implementation, would handle user_created/user_found
        pass

    def _subscribe_to_memory(self) -> None:
        """Subscribe to memory.out events."""

        async def on_batch_processed(payload: dict) -> dict:
            """Handle batch processed event."""
            correlation_id = UUID(payload.get("correlation_id"))
            conversation_id = UUID(payload.get("conversation_id"))
            telegram_chat_id = payload.get("telegram_chat_id")

            # Update state
            state = self._states.get(correlation_id)
            if state:
                state.batch_processed = True
                state.user_id = conversation_id
                state.updated_at = datetime.utcnow()

            # Build context
            command = BuildContextCommand(
                conversation_id=conversation_id,
                telegram_chat_id=telegram_chat_id,
                last_n_messages=50,
            )
            await self._producer.publish(
                topic="memory.in",
                action="build_context",
                payload=command.model_dump(),
                correlation_id=str(correlation_id),
            )
            return {"status": "context_building_started"}

        async def on_context_built(payload: dict) -> dict:
            """Handle context built event."""
            correlation_id = UUID(payload.get("correlation_id"))
            conversation_id = UUID(payload.get("conversation_id"))
            telegram_chat_id = payload.get("telegram_chat_id")
            context = payload.get("context", "")

            # Update state
            state = self._states.get(correlation_id)
            if state:
                state.context = context
                state.updated_at = datetime.utcnow()

            # Generate reply
            command = GenerateReplyCommand(
                conversation_id=conversation_id,
                telegram_chat_id=telegram_chat_id,
                context=context,
            )
            await self._producer.publish(
                topic="llm.in",
                action="generate_reply",
                payload=command.model_dump(),
                correlation_id=str(correlation_id),
            )
            return {"status": "reply_generation_started"}

        self._consumer.subscribe(
            topic="memory.out",
            action="batch_processed",
            schema=dict,
            handler=on_batch_processed,
        )

        self._consumer.subscribe(
            topic="memory.out",
            action="context_built",
            schema=dict,
            handler=on_context_built,
        )

    def _subscribe_to_llm(self) -> None:
        """Subscribe to llm.out events."""

        async def on_reply_generated(payload: dict) -> dict:
            """Handle reply generated event."""
            correlation_id = UUID(payload.get("correlation_id"))
            telegram_chat_id = payload.get("telegram_chat_id")
            messages = payload.get("messages", [])

            # Update state
            state = self._states.get(correlation_id)
            if state:
                state.reply_messages = messages
                state.updated_at = datetime.utcnow()

            # Send message via telegram_clients
            for text in messages:
                command = SendMessageCommand(
                    chat_id=telegram_chat_id,
                    text=text,
                )
                await self._producer.publish(
                    topic="telegram_clients.in",
                    action="send_message",
                    payload=command.model_dump(),
                    correlation_id=str(correlation_id),
                )

            return {"status": "messages_sending"}

        async def on_reply_suppressed(payload: dict) -> dict:
            """Handle reply suppressed event."""
            correlation_id = UUID(payload.get("correlation_id"))
            reason = payload.get("reason", "unknown")

            # Clean up state
            self._states.pop(correlation_id, None)

            return {"status": "reply_suppressed", "reason": reason}

        self._consumer.subscribe(
            topic="llm.out",
            action="reply_generated",
            schema=dict,
            handler=on_reply_generated,
        )

        self._consumer.subscribe(
            topic="llm.out",
            action="reply_suppressed",
            schema=dict,
            handler=on_reply_suppressed,
        )
