import json
from pathlib import Path

import pytest
from sqlalchemy import select

from src.modules.memory.constants import EMBEDDING_DIM
from src.modules.memory.models import Message, VectorRecord
from src.modules.memory.reference_import import (
    extract_text,
    load_reference_export,
    parse_telegram_export,
)
from src.modules.memory.repository import ConversationRepository


def test_extract_text_joins_entities():
    assert extract_text("hi") == "hi"
    assert (
        extract_text([{"type": "plain", "text": "ну "}, {"type": "bold", "text": "да"}]) == "ну да"
    )


def test_parse_telegram_export_maps_peer_to_outgoing(tmp_path: Path):
    payload = {
        "name": "Любимая",
        "type": "personal_chat",
        "id": 757925687,
        "messages": [
            {
                "id": 1,
                "type": "message",
                "from": "Григорий",
                "from_id": "user303486120",
                "text": "Привет",
            },
            {
                "id": 2,
                "type": "message",
                "from": "Любимая",
                "from_id": "user757925687",
                "text": [{"type": "plain", "text": "привет!"}],
            },
            {"id": 3, "type": "service", "text": ""},
            {
                "id": 4,
                "type": "message",
                "from": "Григорий",
                "from_id": "user303486120",
                "text": "",
            },
        ],
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    parsed = parse_telegram_export(path)
    assert parsed.telegram_chat_id == -757925687
    assert [(t.direction, t.text) for t in parsed.turns] == [
        ("incoming", "Привет"),
        ("outgoing", "привет!"),
    ]


class _StubLLM:
    async def cluster_topics(self, numbered: str) -> str:
        seqs = [int(line.split("|", 1)[0]) for line in numbered.splitlines() if line]
        return json.dumps([{"topic": "стиль общения", "ids": seqs, "kind": "topic"}])

    async def embed(self, texts, *, role):
        return [[0.25] * EMBEDDING_DIM for _ in texts]


@pytest.mark.asyncio
async def test_load_reference_export_writes_reference_kind(db_session, tmp_path: Path):
    payload = {
        "name": "Любимая",
        "id": 42,
        "messages": [
            {
                "id": i,
                "type": "message",
                "from": "Григорий" if i % 2 else "Любимая",
                "from_id": "user1" if i % 2 else "user42",
                "text": f"m{i}",
            }
            for i in range(1, 5)
        ],
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    stats = await load_reference_export(db_session, _StubLLM(), path)
    await db_session.commit()
    assert stats["messages"] == 4
    assert stats["topics"] == 1
    conv = await ConversationRepository().get_by_chat_id(db_session, -42, channel="telegram")
    assert conv is not None
    msgs = list((await db_session.execute(select(Message))).scalars().all())
    assert len(msgs) == 4
    records = list((await db_session.execute(select(VectorRecord))).scalars().all())
    assert len(records) == 1
    assert records[0].kind == "reference"
    assert records[0].seq_from == 1
    assert records[0].seq_to == 4
    assert records[0].text == "стиль общения"


@pytest.mark.asyncio
async def test_load_reference_skips_failed_window_and_continues(
    db_session, tmp_path: Path, monkeypatch
):
    monkeypatch.setattr("src.modules.memory.reference_import.REFERENCE_CLUSTER_WINDOW", 2)
    monkeypatch.setattr("src.modules.memory.reference_import._CLUSTER_RETRIES", 1)

    class FlakyLLM(_StubLLM):
        async def cluster_topics(self, numbered: str) -> str:
            seqs = [int(line.split("|", 1)[0]) for line in numbered.splitlines() if line]
            if seqs and seqs[0] == 1:
                return "not-json"
            return json.dumps([{"topic": "later", "ids": seqs, "kind": "topic"}])

    payload = {
        "name": "Любимая",
        "id": 7,
        "messages": [
            {
                "id": i,
                "type": "message",
                "from": "Григорий" if i % 2 else "Любимая",
                "from_id": "user1" if i % 2 else "user7",
                "text": f"m{i}",
            }
            for i in range(1, 5)
        ],
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    stats = await load_reference_export(db_session, FlakyLLM(), path)
    assert stats["topics"] == 1
    records = list((await db_session.execute(select(VectorRecord))).scalars().all())
    assert records[0].seq_from == 3
