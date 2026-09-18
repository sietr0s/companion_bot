from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.main import app
from src.modules.memory.constants import EMBEDDING_DIM
from src.modules.memory.repository import (
    ConversationRepository,
    VectorRecordRepository,
)
from tests.conftest import TestSessionLocal
from tests.modules.memory.seed import insert_message


@pytest_asyncio.fixture
async def test_client_with_db() -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_and_get_topic_http(
    test_client_with_db: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
) -> None:
    conv = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": 901, "user_id": uuid4()},
    )
    await insert_message(db_session, conv.id, text="привет", sequence_number=1)
    record = await VectorRecordRepository().create(
        db_session,
        {
            "conversation_id": conv.id,
            "text": "Приветствия",
            "embedding": [0.2] * EMBEDDING_DIM,
            "seq_from": 1,
            "seq_to": 1,
        },
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    listed = await test_client_with_db.get(
        f"/api/v1/public/memory/conversations/{conv.id}/topics",
        headers=headers,
    )
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["title"] == "Приветствия"
    assert "embedding" not in body[0]

    detail = await test_client_with_db.get(
        f"/api/v1/public/memory/conversations/{conv.id}/topics/{record.id}",
        headers=headers,
    )
    assert detail.status_code == 200
    data = detail.json()
    assert [m["text"] for m in data["messages"]] == ["привет"]
