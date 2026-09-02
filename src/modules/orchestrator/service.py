"""Orchestrator: routes companion pipeline over the message bus."""

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.domain.chat import Message, message_texts
from src.modules.orchestrator.schemas.state import OrchestratorState

logger = logging.getLogger(__name__)


class OrchestratorService:
    def __init__(self, message_consumer: MessageConsumer, message_producer: MessageProducer) -> None:
        self._consumer = message_consumer
        self._producer = message_producer
        self._states: dict[int, OrchestratorState] = {}

    def register_all_handlers(self) -> None:
        self._on_telegram_message()
        self._on_stt()
        self._on_batch_ready()
        self._on_memory()
        self._on_llm()
        self._on_message_sent()

    def _state_for_chat(self, chat_id: int) -> OrchestratorState:
        state = self._states.get(chat_id)
        if state is None:
            state = OrchestratorState(correlation_id=uuid4(), telegram_chat_id=chat_id)
            self._states[chat_id] = state
        return state

    def _on_telegram_message(self) -> None:
        @self._consumer.subscribe(BusTopics.TG_MESSAGE_RECEIVED)
        async def on_message_received(payload: dict) -> None:
            text = (payload.get("text") or "").strip()
            chat_id = int(payload["chat_id"])
            account_id = payload.get("account_id") or payload.get("telegram_account_id")
            media = payload.get("media") or []
            types = {
                (item.get("type") if isinstance(item, dict) else getattr(item, "type", None))
                for item in media
            }
            is_audio = bool(types & {"voice", "audio"})
            if not text and not is_audio:
                return
            state = self._state_for_chat(chat_id)
            state.telegram_account_id = UUID(str(account_id)) if account_id else None
            state.updated_at = datetime.now(UTC)
            if not text and is_audio:
                first = media[0]
                fid = (
                    first.get("telegram_id")
                    if isinstance(first, dict)
                    else getattr(first, "telegram_id", None)
                )
                media_type = (
                    first.get("type")
                    if isinstance(first, dict)
                    else getattr(first, "type", "voice")
                )
                await self._producer.publish(
                    BusTopics.STT_TRANSCRIBE,
                    {
                        "account_id": str(state.telegram_account_id) if state.telegram_account_id else None,
                        "chat_id": chat_id,
                        "message_id": payload.get("message_id"),
                        "telegram_file_id": fid,
                        "media_type": media_type or "voice",
                        "reply_to": payload.get("reply_to"),
                        "forward_from": payload.get("forward_from"),
                    },
                )
                return
            state.current_message = text
            message = Message(
                text=text,
                message_type=(
                    media[0].get("type") if media and isinstance(media[0], dict) else None
                )
                or "text",
                direction="incoming",
                reply_to=payload.get("reply_to"),
                forward_from=payload.get("forward_from"),
                telegram_message_id=payload.get("message_id"),
            )
            await self._producer.publish(
                BusTopics.BATCH_ADD_MESSAGE,
                {
                    "telegram_chat_id": chat_id,
                    "telegram_account_id": str(state.telegram_account_id) if state.telegram_account_id else None,
                    "message": message.model_dump(mode="json"),
                },
            )

    def _on_stt(self) -> None:
        @self._consumer.subscribe(BusTopics.STT_TRANSCRIBED)
        async def on_transcribed(payload: dict) -> None:
            chat_id = int(payload["chat_id"])
            account_id = payload.get("account_id")
            state = self._state_for_chat(chat_id)
            if account_id:
                state.telegram_account_id = UUID(str(account_id))
            text = (payload.get("text") or "").strip()
            if not text:
                return
            state.current_message = text
            message = Message(
                text=text,
                message_type=payload.get("media_type") or "voice",
                direction="incoming",
                reply_to=payload.get("reply_to"),
                forward_from=payload.get("forward_from"),
                telegram_message_id=payload.get("message_id"),
            )
            await self._producer.publish(
                BusTopics.BATCH_ADD_MESSAGE,
                {
                    "telegram_chat_id": chat_id,
                    "telegram_account_id": str(state.telegram_account_id) if state.telegram_account_id else None,
                    "message": message.model_dump(mode="json"),
                },
            )

        @self._consumer.subscribe(BusTopics.STT_TRANSCRIBE_FAILED)
        async def on_transcribe_failed(payload: dict) -> None:
            logger.warning("stt failed: %s", payload.get("reason"))

    def _on_batch_ready(self) -> None:
        @self._consumer.subscribe(BusTopics.BATCH_READY)
        async def on_batch_ready(payload: dict) -> None:
            chat_id = int(payload["telegram_chat_id"])
            account_id = payload.get("telegram_account_id")
            raw_messages = payload.get("messages") or []
            state = self._state_for_chat(chat_id)
            if account_id:
                state.telegram_account_id = UUID(str(account_id))
            messages = [
                {"text": item, "message_type": "text", "direction": "incoming"}
                if isinstance(item, str)
                else item
                for item in raw_messages
            ]
            await self._producer.publish(
                BusTopics.MEMORY_PROCESS_BATCH,
                {
                    "telegram_chat_id": chat_id,
                    "telegram_account_id": str(state.telegram_account_id) if state.telegram_account_id else None,
                    "conversation_id": str(state.conversation_id) if state.conversation_id else None,
                    "messages": messages,
                    "batch_id": payload.get("batch_id"),
                },
            )

    def _on_memory(self) -> None:
        @self._consumer.subscribe(BusTopics.MEMORY_BATCH_PROCESSED)
        async def on_batch_processed(payload: dict) -> None:
            chat_id = int(payload["telegram_chat_id"])
            conversation_id = UUID(str(payload["conversation_id"]))
            state = self._state_for_chat(chat_id)
            state.conversation_id = conversation_id
            if payload.get("telegram_account_id"):
                state.telegram_account_id = UUID(str(payload["telegram_account_id"]))
            await self._producer.publish(
                BusTopics.MEMORY_BUILD_CONTEXT,
                {
                    "conversation_id": str(conversation_id),
                    "telegram_chat_id": chat_id,
                    "telegram_account_id": str(state.telegram_account_id) if state.telegram_account_id else None,
                    "batch_messages": payload.get("messages") or [],
                    "last_n_messages": 50,
                },
            )

        @self._consumer.subscribe(BusTopics.MEMORY_CONTEXT_BUILT)
        async def on_context_built(payload: dict) -> None:
            chat_id = int(payload["telegram_chat_id"])
            conversation_id = UUID(str(payload["conversation_id"]))
            state = self._state_for_chat(chat_id)
            state.context = payload.get("context", "")
            state.conversation_id = conversation_id
            await self._producer.publish(
                BusTopics.LLM_GENERATE_REPLY,
                {
                    "conversation_id": str(conversation_id),
                    "telegram_chat_id": chat_id,
                    "telegram_account_id": str(state.telegram_account_id) if state.telegram_account_id else None,
                    "context": state.context,
                },
            )

    def _on_llm(self) -> None:
        @self._consumer.subscribe(BusTopics.LLM_REPLY_GENERATED)
        async def on_reply_generated(payload: dict) -> None:
            chat_id = int(payload["telegram_chat_id"])
            account_id = payload.get("telegram_account_id")
            messages = payload.get("messages") or []
            texts = message_texts(messages)
            state = self._state_for_chat(chat_id)
            state.reply_messages = texts
            if not account_id:
                return
            for text in texts:
                await self._producer.publish(
                    BusTopics.TG_MESSAGE_SEND,
                    {
                        "account_id": str(account_id),
                        "chat_id": chat_id,
                        "text": text,
                    },
                )

        @self._consumer.subscribe(BusTopics.LLM_REPLY_SUPPRESSED)
        async def on_reply_suppressed(payload: dict) -> None:
            chat_id = payload.get("telegram_chat_id")
            if chat_id is not None:
                self._states.pop(int(chat_id), None)

    def _on_message_sent(self) -> None:
        @self._consumer.subscribe(BusTopics.TG_MESSAGE_SENT)
        async def on_message_sent(payload: dict) -> None:
            chat_id = int(payload["chat_id"])
            state = self._states.get(chat_id)
            if not state or not state.conversation_id or not state.reply_messages:
                return
            await self._producer.publish(
                BusTopics.MEMORY_UPDATE,
                {
                    "conversation_id": str(state.conversation_id),
                    "telegram_chat_id": chat_id,
                    "outgoing_messages": state.reply_messages,
                    "delivery_status": "delivered" if payload.get("success", True) else "failed",
                },
            )
