from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.domain.chat import Message
from src.modules.behavior.classifiers import FakeIntakeClassifier
from src.modules.behavior.repository import BehaviorRepository
from src.modules.behavior.schemas.events import DecideDeliveryCommand, DecideIntakeCommand
from src.modules.behavior.service import BehaviorService
from src.modules.telegram_clients.models import TelegramAccount


@pytest.mark.asyncio
async def test_decide_intake_ignore_when_forced(db_session):
    account = TelegramAccount(phone="+79001110000", session_file="/tmp/s", is_connected=True)
    db_session.add(account)
    await db_session.flush()
    producer = AsyncMock()
    svc = BehaviorService(
        producer,
        BehaviorRepository(),
        FakeIntakeClassifier(needs_reply=0),
        rng=__import__("random").Random(1),
    )
    event = await svc.decide_intake(
        db_session,
        DecideIntakeCommand(
            conversation_id=uuid4(),
            telegram_account_id=account.id,
            telegram_chat_id=1,
            batch_messages=[Message(text="ok thanks whatever")],
        ),
    )
    assert event.needs_reply == 0
    assert "ignore" in event.scores


@pytest.mark.asyncio
async def test_decide_delivery_blocks_voice_on_url(db_session):
    account = TelegramAccount(phone="+79001110001", session_file="/tmp/s2", is_connected=True)
    db_session.add(account)
    await db_session.flush()
    producer = AsyncMock()
    svc = BehaviorService(producer, BehaviorRepository(), FakeIntakeClassifier())
    event = await svc.decide_delivery(
        db_session,
        DecideDeliveryCommand(
            conversation_id=uuid4(),
            telegram_account_id=account.id,
            telegram_chat_id=1,
            messages=[Message(text="see https://t.me/x and more words here")],
            asked_voice=1,
        ),
    )
    assert event.action == "text"
    assert event.blocked_voice
