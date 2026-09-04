"""Orchestrator: routes companion pipeline over the message bus."""

import asyncio
import logging
import random
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
        self._states: dict[tuple[str, int], OrchestratorState] = {}

    def register_all_handlers(self) -> None:
        self._on_telegram_message()
        self._on_stt()
        self._on_batch_ready()
        self._on_memory()
        self._on_behavior()
        self._on_llm()
        self._on_tts()
        self._on_message_sent()

    @staticmethod
    def _state_key(account_id: UUID | str | None, chat_id: int) -> tuple[str, int]:
        return (str(account_id) if account_id else "", int(chat_id))

    def _state_for(self, account_id: UUID | str | None, chat_id: int) -> OrchestratorState:
        key = self._state_key(account_id, chat_id)
        state = self._states.get(key)
        if state is None:
            state = OrchestratorState(
                correlation_id=uuid4(),
                telegram_chat_id=chat_id,
                telegram_account_id=UUID(str(account_id)) if account_id else None,
            )
            self._states[key] = state
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
            state = self._state_for(account_id, chat_id)
            if account_id:
                state.telegram_account_id = UUID(str(account_id))
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
            state = self._state_for(account_id, chat_id)
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
            state = self._state_for(account_id, chat_id)
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
            state = self._state_for(payload.get("telegram_account_id"), chat_id)
            state.conversation_id = conversation_id
            if payload.get("telegram_account_id"):
                state.telegram_account_id = UUID(str(payload["telegram_account_id"]))
            state.batch_messages = list(payload.get("messages") or [])
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
            state = self._state_for(payload.get("telegram_account_id"), chat_id)
            state.context = payload.get("context", "")
            state.conversation_id = conversation_id
            if payload.get("batch_messages"):
                state.batch_messages = list(payload.get("batch_messages") or [])
            await self._producer.publish(
                BusTopics.BEHAVIOR_DECIDE_INTAKE,
                {
                    "conversation_id": str(conversation_id),
                    "telegram_chat_id": chat_id,
                    "telegram_account_id": str(state.telegram_account_id) if state.telegram_account_id else None,
                    "context": state.context,
                    "batch_messages": state.batch_messages,
                },
            )

    def _on_behavior(self) -> None:
        @self._consumer.subscribe(BusTopics.BEHAVIOR_INTAKE_DECIDED)
        async def on_intake_decided(payload: dict) -> None:
            chat_id = int(payload["telegram_chat_id"])
            account_id = payload.get("telegram_account_id")
            state = self._state_for(account_id, chat_id)
            if payload.get("action") == "ignore":
                self._states.pop(self._state_key(account_id, chat_id), None)
                return
            state.asked_voice = int(payload.get("asked_voice") or 0)
            if not state.conversation_id:
                return
            await self._producer.publish(
                BusTopics.LLM_GENERATE_REPLY,
                {
                    "conversation_id": str(state.conversation_id),
                    "telegram_chat_id": chat_id,
                    "telegram_account_id": str(state.telegram_account_id) if state.telegram_account_id else None,
                    "context": state.context or "",
                },
            )

        @self._consumer.subscribe(BusTopics.BEHAVIOR_DELIVERY_DECIDED)
        async def on_delivery_decided(payload: dict) -> None:
            chat_id = int(payload["telegram_chat_id"])
            account_id = payload.get("telegram_account_id")
            state = self._state_for(account_id, chat_id)
            texts = list(state.reply_messages or [])
            if not texts and payload.get("text"):
                texts = [payload["text"]]
            state.pending_outgoing_texts = texts
            action = payload.get("action") or "text"
            state.pending_delivery = action
            if not account_id:
                return
            if action == "voice":
                try:
                    await self._producer.publish(
                        BusTopics.TG_CHAT_ACTION,
                        {
                            "account_id": str(account_id),
                            "chat_id": chat_id,
                            "action": "record_audio",
                        },
                    )
                except Exception:
                    logger.exception("record_audio action failed")
                await asyncio.sleep(random.uniform(1.0, 1.5))
                joined = ". ".join(texts)
                await self._producer.publish(
                    BusTopics.TTS_SYNTHESIZE,
                    {
                        "account_id": str(account_id),
                        "chat_id": chat_id,
                        "text": joined,
                    },
                )
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

    def _on_tts(self) -> None:
        @self._consumer.subscribe(BusTopics.TTS_SYNTHESIZED)
        async def on_synthesized(payload: dict) -> None:
            chat_id = int(payload["chat_id"])
            account_id = payload.get("account_id") or payload.get("telegram_account_id")
            state = self._states.get(self._state_key(account_id, chat_id))
            texts = list(state.pending_outgoing_texts) if state else []
            joined = ". ".join(texts) or payload.get("text") or ""
            await self._producer.publish(
                BusTopics.TG_MESSAGE_SEND_VOICE,
                {
                    "account_id": str(account_id) if account_id else None,
                    "chat_id": chat_id,
                    "path": payload.get("path"),
                    "text": joined,
                },
            )

        @self._consumer.subscribe(BusTopics.TTS_SYNTHESIZE_SKIPPED)
        async def on_skipped(payload: dict) -> None:
            chat_id = int(payload["chat_id"])
            account_id = payload.get("account_id") or payload.get("telegram_account_id")
            state = self._states.get(self._state_key(account_id, chat_id))
            texts = list(state.pending_outgoing_texts) if state else []
            if state:
                state.pending_delivery = "text"
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

    def _on_llm(self) -> None:
        @self._consumer.subscribe(BusTopics.LLM_REPLY_GENERATED)
        async def on_reply_generated(payload: dict) -> None:
            chat_id = int(payload["telegram_chat_id"])
            account_id = payload.get("telegram_account_id")
            messages = payload.get("messages") or []
            texts = message_texts(messages)
            state = self._state_for(account_id, chat_id)
            state.reply_messages = list(texts)
            if not account_id:
                return
            await self._producer.publish(
                BusTopics.BEHAVIOR_DECIDE_DELIVERY,
                {
                    "conversation_id": str(state.conversation_id) if state.conversation_id else None,
                    "telegram_chat_id": chat_id,
                    "telegram_account_id": str(account_id),
                    "messages": messages,
                    "batch_messages": state.batch_messages,
                    "asked_voice": state.asked_voice,
                },
            )

        @self._consumer.subscribe(BusTopics.LLM_REPLY_SUPPRESSED)
        async def on_reply_suppressed(payload: dict) -> None:
            chat_id = payload.get("telegram_chat_id")
            if chat_id is None:
                return
            account_id = payload.get("telegram_account_id")
            self._states.pop(self._state_key(account_id, int(chat_id)), None)

    def _on_message_sent(self) -> None:
        @self._consumer.subscribe(BusTopics.TG_MESSAGE_SENT)
        async def on_message_sent(payload: dict) -> None:
            chat_id = int(payload["chat_id"])
            account_id = payload.get("telegram_account_id") or payload.get("account_id")
            text = payload.get("text")
            state = self._states.get(self._state_key(account_id, chat_id))
            if not state or not state.conversation_id:
                return
            outgoing = [text] if text else list(state.reply_messages or [])
            if not outgoing:
                return
            if text and state.reply_messages and text in state.reply_messages:
                remaining = list(state.reply_messages)
                remaining.remove(text)
                state.reply_messages = remaining
            await self._producer.publish(
                BusTopics.MEMORY_UPDATE,
                {
                    "conversation_id": str(state.conversation_id),
                    "telegram_chat_id": chat_id,
                    "outgoing_messages": outgoing,
                    "delivery_status": "delivered" if payload.get("success", True) else "failed",
                },
            )
            if payload.get("success", True) and account_id:
                channel = "voice" if payload.get("message_type") == "voice" else "text"
                await self._producer.publish(
                    BusTopics.BEHAVIOR_NOTE_DELIVERY,
                    {
                        "telegram_account_id": str(account_id),
                        "telegram_chat_id": chat_id,
                        "channel": channel,
                    },
                )
            if not state.reply_messages:
                self._states.pop(self._state_key(account_id, chat_id), None)
