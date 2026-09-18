from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.domain.chat import Batch, Message
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
            channel="telegram",
            account_id=account.id,
            chat_id=1,
            batch_messages=Batch(
                channel="telegram",
                chat_id=1,
                account_id=account.id,
                messages=[Message(text="ok thanks whatever")],
            ),
        ),
    )
    assert event.needs_reply == 0
    assert "ignore" in event.scores


@pytest.mark.asyncio
async def test_decide_intake_classifies_recent_window(db_session):
    account = TelegramAccount(phone="+79001110002", session_file="/tmp/s3", is_connected=True)
    db_session.add(account)
    await db_session.flush()
    seen: list[str] = []

    class Capture:
        async def classify(self, user_text: str):
            seen.append(user_text)
            return 1, 0

    producer = AsyncMock()
    svc = BehaviorService(
        producer, BehaviorRepository(), Capture(), rng=__import__("random").Random(1)
    )
    await svc.decide_intake(
        db_session,
        DecideIntakeCommand(
            conversation_id=uuid4(),
            channel="telegram",
            account_id=account.id,
            chat_id=1,
            batch_messages=Batch(
                channel="telegram",
                chat_id=1,
                account_id=account.id,
                messages=[Message(text="ok", direction="incoming")],
            ),
            recent=[
                Message(text="hello", direction="incoming"),
                Message(text="hi there", direction="outgoing"),
                Message(text="ok", direction="incoming"),
            ],
        ),
    )
    assert seen
    assert "User: hello" in seen[0]
    assert "Assistant: hi there" in seen[0]
    assert "User: ok" in seen[0]


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
            channel="telegram",
            account_id=account.id,
            chat_id=1,
            messages=[Message(text="see https://t.me/x and more words here")],
            asked_voice=1,
        ),
    )
    assert event.action == "text"
    assert event.blocked_voice


@pytest.mark.asyncio
async def test_decide_delivery_blocks_voice_on_instagram(db_session):
    account = TelegramAccount(phone="+79001110009", session_file="/tmp/s9", is_connected=True)
    db_session.add(account)
    await db_session.flush()
    producer = AsyncMock()
    svc = BehaviorService(producer, BehaviorRepository(), FakeIntakeClassifier())
    event = await svc.decide_delivery(
        db_session,
        DecideDeliveryCommand(
            conversation_id=uuid4(),
            channel="instagram",
            account_id=account.id,
            chat_id=11,
            messages=[
                Message(
                    text="this is a long enough spoken reply without urls or digits here"
                )
            ],
            asked_voice=1,
        ),
    )
    assert event.action == "text"
    assert event.blocked_voice
