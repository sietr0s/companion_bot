"""Behavior decisions on the bus."""

from __future__ import annotations

import random
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.core.bus_topics import BusTopics
from src.core.exceptions import ValidationError
from src.domain.chat import Message, message_texts
from src.modules.behavior.classifiers import format_intake_window
from src.modules.behavior.engine import (
    ChatSnapshot,
    DecisionContext,
    LifeSnapshot,
    decide,
)
from src.modules.behavior.policies import DELIVERY_POLICY, INTAKE_POLICY
from src.modules.behavior.schemas.events import (
    DecideDeliveryCommand,
    DecideIntakeCommand,
    DeliveryDecidedEvent,
    IntakeDecidedEvent,
    NoteDeliveryCommand,
)
from src.modules.behavior.scoring import detect_emotion, strip_emotion_suffix

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.bus.interface import MessageProducer
    from src.modules.behavior.classifiers import IntakeClassifier
    from src.modules.behavior.repository import BehaviorRepository


def _incoming_blob(messages: list[Message]) -> tuple[str, tuple[str, ...]]:
    texts = message_texts(messages)
    types = tuple(
        (m.message_type if isinstance(m, Message) else m.get("message_type", "text"))
        for m in messages
    )
    return " ".join(texts), types


class BehaviorService:
    def __init__(
        self,
        producer: MessageProducer,
        repo: BehaviorRepository,
        classifier: IntakeClassifier,
        rng: random.Random | None = None,
    ) -> None:
        self._producer = producer
        self._repo = repo
        self._classifier = classifier
        self._rng = rng or random.Random()

    async def decide_intake(
        self, session: AsyncSession, command: DecideIntakeCommand
    ) -> IntakeDecidedEvent:
        incoming, _ = _incoming_blob(command.batch_messages.messages)
        now = datetime.now(UTC)
        if command.account_id is None:
            raise ValidationError("account_id is required for intake")
        window = format_intake_window(command.recent, command.batch_messages)
        needs_reply, asked_voice = await self._classifier.classify(window)
        row = await self._repo.get_or_create_account(
            session, command.account_id, now, self._rng
        )
        life = LifeSnapshot(row.activity, row.mood)
        ctx = DecisionContext(
            incoming_text=incoming,
            life=life,
            needs_reply=needs_reply,
            asked_voice=asked_voice,
            now=now,
        )
        decision = decide(INTAKE_POLICY, ctx, self._rng)
        action = decision.action
        scores = decision.scores
        event = IntakeDecidedEvent(
            conversation_id=command.conversation_id,
            channel=command.channel,
            account_id=command.account_id,
            chat_id=command.chat_id,
            action=action,
            scores=scores,
            probabilities=decision.probabilities,
            activity=life.activity,
            mood=life.mood,
            needs_reply=needs_reply,
            asked_voice=asked_voice,
        )
        await self._producer.publish(
            BusTopics.BEHAVIOR_INTAKE_DECIDED, event.model_dump(mode="json")
        )
        return event

    async def decide_delivery(
        self, session: AsyncSession, command: DecideDeliveryCommand
    ) -> DeliveryDecidedEvent:
        incoming, types = _incoming_blob(command.batch_messages)
        joined = ". ".join(message_texts(command.messages))
        body, suffix_emotion = strip_emotion_suffix(joined)
        emotion = detect_emotion(
            body, command.emotion if command.emotion is not None else suffix_emotion
        )
        now = datetime.now(UTC)
        if command.account_id is None:
            raise ValidationError("account_id is required for delivery")
        account = await self._repo.get_or_create_account(
            session, command.account_id, now, self._rng
        )
        chat_row = await self._repo.get_or_create_chat(
            session, command.account_id, command.chat_id
        )
        life = LifeSnapshot(account.activity, account.mood)
        chat = ChatSnapshot(chat_row.consecutive_voice_out, chat_row.last_delivery)
        ctx = DecisionContext(
            incoming_text=incoming,
            incoming_types=types,
            outgoing_text=body,
            life=life,
            chat=chat,
            asked_voice=command.asked_voice,
            emotion=emotion,
            now=now,
        )
        decision = decide(DELIVERY_POLICY, ctx, self._rng)
        action = decision.action
        scores = decision.scores
        blocked = decision.blocked
        event = DeliveryDecidedEvent(
            conversation_id=command.conversation_id,
            channel=command.channel,
            account_id=command.account_id,
            chat_id=command.chat_id,
            action=action,
            text=body,
            scores=scores,
            probabilities=decision.probabilities,
            blocked_voice="voice" in blocked,
            block_reasons=list(blocked.values()),
            incoming_types=list(types),
            activity=life.activity,
            mood=life.mood,
        )
        await self._producer.publish(
            BusTopics.BEHAVIOR_DELIVERY_DECIDED, event.model_dump(mode="json")
        )
        return event

    async def note_delivery(self, session: AsyncSession, command: NoteDeliveryCommand) -> None:
        await self._repo.note_delivery(
            session,
            command.account_id,
            command.chat_id,
            command.delivery,
        )
