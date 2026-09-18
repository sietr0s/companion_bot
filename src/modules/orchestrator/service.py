"""Orchestrator: routes companion pipeline over the message bus."""

import asyncio
import logging
import random
from uuid import UUID, uuid4

from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.domain.chat import Batch, ChatRef, ConversationContext, Message, message_texts
from src.modules.behavior.report import format_decision_log
from src.modules.orchestrator.schemas.state import OrchestratorState

logger = logging.getLogger(__name__)


class OrchestratorService:
    def __init__(
        self, message_consumer: MessageConsumer, message_producer: MessageProducer
    ) -> None:
        self._consumer = message_consumer
        self._producer = message_producer
        self._states: dict[tuple[str, int], OrchestratorState] = {}
        self._background: set[asyncio.Task] = set()

    def register_all_handlers(self) -> None:
        self._on_telegram_message()
        self._on_stt()
        self._on_batch_ready()
        self._on_memory()
        self._on_behavior()
        self._on_llm()
        self._on_tts()
        self._on_message_sent()

    def _state_key(
        self, channel: str, account_id: UUID | str | None, chat_id: int
    ) -> tuple[str, str, int]:
        return (channel, str(account_id) if account_id else "", int(chat_id))

    def _state_for(
        self, channel: str, account_id: UUID | str | None, chat_id: int
    ) -> OrchestratorState:
        key = self._state_key(channel, account_id, chat_id)
        state = self._states.get(key)
        if state is None:
            state = OrchestratorState(
                correlation_id=uuid4(),
                chat=ChatRef(
                    channel=channel,  # type: ignore[arg-type]
                    chat_id=int(chat_id),
                    account_id=UUID(str(account_id)) if account_id else None,
                ),
            )
            self._states[key] = state
        return state

    @staticmethod
    def _with_channel(payload: dict) -> dict:
        if payload.get("channel") in ("telegram", "instagram"):
            return payload
        return {**payload, "channel": "telegram"}

    def _state_from_payload(self, payload: dict) -> OrchestratorState:
        ref = ChatRef.from_payload(self._with_channel(payload))
        return self._state_for(ref.channel, ref.account_id, ref.chat_id)

    def _merge_chat(self, state: OrchestratorState, payload: dict) -> ChatRef:
        state.chat = state.chat.merged(ChatRef.from_payload(self._with_channel(payload)))
        return state.chat

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    async def wait_background(self) -> None:
        if self._background:
            await asyncio.gather(*self._background, return_exceptions=True)

    async def _deliver_voice(self, ids: dict, texts: list[str]) -> None:
        await self._producer.publish(
            BusTopics.TG_CHAT_ACTION,
            {**ids, "action": "record_audio"},
        )
        await asyncio.sleep(random.uniform(1.0, 1.5))
        joined = ". ".join(texts)
        await self._producer.publish(
            BusTopics.TTS_SYNTHESIZE,
            {**ids, "text": joined},
        )

    @staticmethod
    def _as_messages(raw: list) -> list[Message]:
        out: list[Message] = []
        for item in raw:
            if isinstance(item, Message):
                out.append(item)
            elif isinstance(item, str):
                out.append(Message(text=item, direction="incoming"))
            else:
                out.append(Message.model_validate(item))
        return out

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
            state = self._state_from_payload(payload)
            self._merge_chat(state, payload)
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
                        **state.chat.adapter_ids(),
                        "message_id": payload.get("message_id"),
                        "telegram_file_id": fid,
                        "media_type": media_type or "voice",
                        "reply_to": payload.get("reply_to"),
                        "forward_from": payload.get("forward_from"),
                    },
                )
                return
            message = Message(
                text=text,
                message_type=(
                    media[0].get("type") if media and isinstance(media[0], dict) else None
                )
                or "text",
                direction="incoming",
                reply_to=payload.get("reply_to"),
                forward_from=payload.get("forward_from"),
                message_id=payload.get("message_id"),
            )
            await self._producer.publish(
                BusTopics.BATCH_ADD_MESSAGE,
                {
                    **state.chat.bus_ids(),
                    "message": message.model_dump(mode="json"),
                },
            )

    def _on_stt(self) -> None:
        @self._consumer.subscribe(BusTopics.STT_TRANSCRIBED)
        async def on_transcribed(payload: dict) -> None:
            chat_id = int(payload["chat_id"])
            account_id = payload.get("account_id")
            state = self._state_from_payload(payload)
            self._merge_chat(state, payload)
            text = (payload.get("text") or "").strip()
            if not text:
                return
            message = Message(
                text=text,
                message_type=payload.get("media_type") or "voice",
                direction="incoming",
                reply_to=payload.get("reply_to"),
                forward_from=payload.get("forward_from"),
                message_id=payload.get("message_id"),
            )
            await self._producer.publish(
                BusTopics.BATCH_ADD_MESSAGE,
                {
                    **state.chat.bus_ids(),
                    "message": message.model_dump(mode="json"),
                },
            )

        @self._consumer.subscribe(BusTopics.STT_TRANSCRIBE_FAILED)
        async def on_transcribe_failed(payload: dict) -> None:
            logger.warning("stt failed: %s", payload.get("reason"))

    def _on_batch_ready(self) -> None:
        @self._consumer.subscribe(BusTopics.BATCH_READY)
        async def on_batch_ready(payload: dict) -> None:
            state = self._state_from_payload(payload)
            batch = Batch.model_validate(payload["batch"])
            state.batch_messages = batch
            await self._producer.publish(
                BusTopics.MEMORY_PROCESS_BATCH,
                {"batch": batch.model_dump(mode="json")},
            )

    # TODO: Шаг хуйни
    def _on_memory(self) -> None:
        @self._consumer.subscribe(BusTopics.MEMORY_BATCH_PROCESSED)
        async def on_batch_processed(payload: dict) -> None:
            state = self._state_from_payload(payload)
            chat = self._merge_chat(state, payload)
            await self._producer.publish(
                BusTopics.MEMORY_BUILD_CONTEXT,
                {
                    **chat.bus_ids(),
                    "last_n_messages": 50,
                },
            )

        @self._consumer.subscribe(BusTopics.MEMORY_CONTEXT_BUILT)
        async def on_context_built(payload: dict) -> None:
            state = self._state_from_payload(payload)
            chat = self._merge_chat(state, payload)
            state.memory = ConversationContext.from_payload(payload)
            await self._producer.publish(
                BusTopics.BEHAVIOR_DECIDE_INTAKE,
                {
                    **chat.bus_ids(),
                    "batch_messages": state.batch_messages.model_dump(mode="json"),
                    "recent": [m.model_dump(mode="json") for m in state.memory.recent_messages()],
                },
            )

    def _on_behavior(self) -> None:
        @self._consumer.subscribe(BusTopics.BEHAVIOR_INTAKE_DECIDED)
        async def on_intake_decided(payload: dict) -> None:
            chat_id = int(payload["telegram_chat_id"])
            account_id = payload.get("telegram_account_id")
            state = self._state_from_payload(payload)
            if payload.get("action") == "ignore":
                logger.info(
                    "\n%s",
                    format_decision_log(
                        stage="intake",
                        action="ignore",
                        text="",
                        probabilities=payload.get("probabilities") or {},
                        scores=payload.get("scores") or {},
                        chat_id=chat_id,
                        activity=payload.get("activity"),
                        mood=payload.get("mood"),
                    ),
                )
                self._states.pop(ChatRef.from_payload(self._with_channel(payload)).state_key(), None)
                return
            state.asked_voice = int(payload.get("asked_voice") or 0)
            if not state.chat.conversation_id:
                return
            await self._producer.publish(
                BusTopics.LLM_GENERATE_REPLY,
                {
                    **state.chat.bus_ids(),
                    "summary": state.memory.summary,
                    "retrieved": [t.model_dump(mode="json") for t in state.memory.retrieved],
                    "references": [t.model_dump(mode="json") for t in state.memory.references],
                    "recent": [b.model_dump(mode="json") for b in state.memory.recent],
                },
            )

        @self._consumer.subscribe(BusTopics.BEHAVIOR_DELIVERY_DECIDED)
        async def on_delivery_decided(payload: dict) -> None:
            state = self._state_from_payload(payload)
            texts = state.reply_messages
            state.pending_outgoing_texts = texts
            action = payload.get("action")
            if not action:
                logger.error("delivery_decided without action chat=%s", payload["telegram_chat_id"])
                return
            state.pending_delivery = action
            state.delivery_report = {
                "action": action,
                "text": "\n".join(texts),
                "probabilities": payload.get("probabilities") or {},
                "scores": payload.get("scores") or {},
                "blocked": payload.get("block_reasons") or [],
                "chat_id": payload["telegram_chat_id"],
                "incoming_types": payload.get("incoming_types") or [],
                "activity": payload.get("activity"),
                "mood": payload.get("mood"),
            }
            if not payload.get("telegram_account_id"):
                return
            ids = state.chat.adapter_ids()
            if action == "voice":
                self._spawn(self._deliver_voice(ids, texts))
                return
            for text in texts:
                await self._producer.publish(
                    BusTopics.TG_MESSAGE_SEND,
                    {**ids, "text": text},
                )

    def _on_tts(self) -> None:
        @self._consumer.subscribe(BusTopics.TTS_SYNTHESIZED)
        async def on_synthesized(payload: dict) -> None:
            account_id = payload.get("account_id") or payload.get("telegram_account_id")
            state = self._states.get(ChatRef.from_payload(self._with_channel(payload)).state_key())
            texts = list(state.pending_outgoing_texts) if state else []
            joined = ". ".join(texts) or payload.get("text") or ""
            await self._producer.publish(
                BusTopics.TG_MESSAGE_SEND_VOICE,
                {
                    **ChatRef.from_payload(self._with_channel(payload)).adapter_ids(),
                    "path": payload.get("path"),
                    "text": joined,
                },
            )

        @self._consumer.subscribe(BusTopics.TTS_SYNTHESIZE_SKIPPED)
        async def on_skipped(payload: dict) -> None:
            chat_id = int(payload["chat_id"])
            account_id = payload.get("account_id") or payload.get("telegram_account_id")
            reason = payload.get("reason") or "unknown"
            state = self._states.get(ChatRef.from_payload(self._with_channel(payload)).state_key())
            texts = list(state.pending_outgoing_texts) if state else []
            if not texts and payload.get("text"):
                texts = [str(payload["text"])]
            logger.warning("TTS failed, sending text fallback chat=%s reason=%s", chat_id, reason)
            if state:
                state.pending_delivery = "text"
                if state.delivery_report is not None:
                    state.delivery_report["action"] = "text"
            if not account_id or not texts:
                self._states.pop(ChatRef.from_payload(self._with_channel(payload)).state_key(), None)
                return
            ids = ChatRef.from_payload(self._with_channel(payload)).adapter_ids()
            for text in texts:
                await self._producer.publish(
                    BusTopics.TG_MESSAGE_SEND,
                    {**ids, "text": text},
                )

    def _on_llm(self) -> None:
        @self._consumer.subscribe(BusTopics.LLM_REPLY_GENERATED)
        async def on_reply_generated(payload: dict) -> None:
            chat_id = int(payload["telegram_chat_id"])
            account_id = payload.get("telegram_account_id")
            messages = payload.get("messages") or []
            texts = message_texts(messages)
            state = self._state_from_payload(payload)
            state.reply_messages = list(texts)
            await self._producer.publish(
                BusTopics.BEHAVIOR_DECIDE_DELIVERY,
                {
                    **state.chat.bus_ids(),
                    "messages": messages,
                    "batch_messages": [
                        m.model_dump(mode="json")
                        for m in (state.batch_messages.messages if state.batch_messages else [])
                    ],
                    "asked_voice": state.asked_voice,
                },
            )

        @self._consumer.subscribe(BusTopics.LLM_REPLY_SUPPRESSED)
        async def on_reply_suppressed(payload: dict) -> None:
            chat_id = payload.get("telegram_chat_id")
            if chat_id is None:
                return
            account_id = payload.get("telegram_account_id")
            self._states.pop(ChatRef.from_payload(self._with_channel(payload)).state_key(), None)

    def _on_message_sent(self) -> None:
        @self._consumer.subscribe(BusTopics.TG_MESSAGE_SENT)
        async def on_message_sent(payload: dict) -> None:
            chat_id = int(payload["chat_id"])
            account_id = payload.get("telegram_account_id") or payload.get("account_id")
            text = payload.get("text")
            state = self._states.get(ChatRef.from_payload(self._with_channel(payload)).state_key())
            if not state or not state.chat.conversation_id:
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
                    **state.chat.bus_ids(),
                    "outgoing_messages": outgoing,
                    "delivery_status": "delivered" if payload.get("success", True) else "failed",
                    "message_type": "voice" if payload.get("message_type") == "voice" else "text",
                },
            )
            if payload.get("success", True) and account_id:
                delivery = "voice" if payload.get("message_type") == "voice" else "text"
                await self._producer.publish(
                    BusTopics.BEHAVIOR_NOTE_DELIVERY,
                    {
                        **state.chat.bus_ids(),
                        "delivery": delivery,
                    },
                )
            if not state.reply_messages:
                report = state.delivery_report or {}
                sent_as = (
                    "voice"
                    if payload.get("message_type") == "voice"
                    else report.get("action") or "text"
                )
                logger.info(
                    "\n%s",
                    format_decision_log(
                        stage="delivery",
                        action=sent_as,
                        text=report.get("text") or (text or ""),
                        probabilities=report.get("probabilities") or {},
                        scores=report.get("scores") or {},
                        blocked=report.get("blocked") or [],
                        chat_id=chat_id,
                        activity=report.get("activity"),
                        mood=report.get("mood"),
                        incoming_types=report.get("incoming_types") or [],
                    ),
                )
                self._states.pop(ChatRef.from_payload(self._with_channel(payload)).state_key(), None)
