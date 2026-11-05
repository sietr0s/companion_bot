from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.memory.constants import EMBEDDING_DIM
from src.modules.memory.repository import (
    ConversationRepository,
    VectorRecordRepository,
)
from tests.modules.memory.seed import insert_message


@pytest.mark.asyncio
async def test_list_and_get_topic_http(
    api_client: AsyncClient,
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
    listed = await api_client.get(
        f"/api/v1/public/memory/conversations/{conv.id}/topics",
        headers=headers,
    )
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["title"] == "Приветствия"
    assert "embedding" not in body[0]

    detail = await api_client.get(
        f"/api/v1/public/memory/conversations/{conv.id}/topics/{record.id}",
        headers=headers,
    )
    assert detail.status_code == 200
    data = detail.json()
    assert [m["text"] for m in data["messages"]] == ["привет"]
