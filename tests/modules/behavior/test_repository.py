from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.modules.behavior.repository import BehaviorRepository
from src.modules.telegram_clients.models import TelegramAccount


@pytest.mark.asyncio
async def test_note_delivery_resets_streak_on_text(db_session):
    account = TelegramAccount(phone="+79001112233", session_file="/tmp/b", is_connected=True)
    db_session.add(account)
    await db_session.flush()
    repo = BehaviorRepository()
    now = datetime.now(UTC)
    await repo.get_or_create_account(db_session, account.id, now, __import__("random").Random(0))
    await repo.note_delivery(db_session, account.id, 1, "voice")
    await repo.note_delivery(db_session, account.id, 1, "voice")
    chat = await repo.get_or_create_chat(db_session, account.id, 1)
    assert chat.consecutive_voice_out == 2
    await repo.note_delivery(db_session, account.id, 1, "text")
    chat = await repo.get_or_create_chat(db_session, account.id, 1)
    assert chat.consecutive_voice_out == 0
    assert chat.last_delivery == "text"
