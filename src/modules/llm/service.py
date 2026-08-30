"""LLM module business logic service."""


from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.llm.schemas_bus import (
    GenerateReplyCommand,
    PostRetrieveCommand,
    PostRetrieveResultEvent,
    PreRetrieveCommand,
    PreRetrieveResultEvent,
    ReplyGeneratedEvent,
    ReplySuppressedEvent,
    SummarizeCommand,
    SummaryGeneratedEvent,
)


class LLMService:
    """Service for LLM-related business logic (stateless)."""

    def __init__(self, message_bus: MessageProducer):
        self._message_bus = message_bus

    async def generate_reply(
        self,
        command: GenerateReplyCommand,
    ) -> ReplyGeneratedEvent | ReplySuppressedEvent:
        """Generate a reply based on context."""
        # In real app, would call LLM provider with persona prompt
        # For now, simplified implementation

        # Decide whether to respond or suppress
        # (In real app, LLM would decide based on context)
        should_respond = len(command.context.strip()) > 0

        if not should_respond:
            event = ReplySuppressedEvent(
                conversation_id=command.conversation_id,
                telegram_chat_id=command.telegram_chat_id,
                reason="empty_context",
            )
        else:
            # Generate 1-3 messages (simplified)
            messages = [f"Response to: {command.context[:100]}..."]

            event = ReplyGeneratedEvent(
                conversation_id=command.conversation_id,
                telegram_chat_id=command.telegram_chat_id,
                messages=messages,
            )

        action = "reply_generated" if isinstance(event, ReplyGeneratedEvent) else "reply_suppressed"

        await self._message_bus.publish(
            topic=BusTopics.LLM_OUT,
            action=action,
            payload=event.model_dump(),
        )

        return event

    async def summarize(
        self,
        command: SummarizeCommand,
    ) -> SummaryGeneratedEvent:
        """Summarize conversation messages."""
        # In real app, would call LLM with summarization prompt
        # For now, simplified implementation

        full_text = "\n".join(command.messages)
        summary = full_text[:command.max_chars] if len(full_text) > command.max_chars else full_text

        event = SummaryGeneratedEvent(
            conversation_id=command.conversation_id,
            summary=summary,
            char_count=len(summary),
        )

        await self._message_bus.publish(
            topic=BusTopics.LLM_OUT,
            action="summary_generated",
            payload=event.model_dump(),
        )

        return event

    async def pre_retrieve(
        self,
        command: PreRetrieveCommand,
    ) -> PreRetrieveResultEvent:
        """Generate search query for RAG (pre-retriever)."""
        # In real app, would use LLM to generate optimal search query
        # For now, simplified implementation

        search_query = command.context[:200]  # Use first 200 chars as query

        event = PreRetrieveResultEvent(
            conversation_id=command.conversation_id,
            search_query=search_query,
        )

        await self._message_bus.publish(
            topic=BusTopics.LLM_OUT,
            action="pre_retrieve_result",
            payload=event.model_dump(),
        )

        return event

    async def post_retrieve(
        self,
        command: PostRetrieveCommand,
    ) -> PostRetrieveResultEvent:
        """Re-rank retrieved candidates (post-retriever)."""
        # In real app, would use LLM to re-rank and select best candidates
        # For now, simplified implementation

        selected = command.candidates[:command.top_k]

        event = PostRetrieveResultEvent(
            conversation_id=command.conversation_id,
            selected_candidates=selected,
            total_candidates=len(command.candidates),
        )

        await self._message_bus.publish(
            topic=BusTopics.LLM_OUT,
            action="post_retrieve_result",
            payload=event.model_dump(),
        )

        return event
