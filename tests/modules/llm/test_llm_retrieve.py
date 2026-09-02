import pytest

from src.bus.in_memory.producer import InMemoryProducer
from src.bus.in_memory.transport import InMemoryTransport
from src.modules.llm.providers.stub import StubChat
from src.modules.llm.service import LLMService
from src.modules.memory.constants import EMBEDDING_DIM
from tests.fakes.embedder import FakeEmbedder


def _svc() -> LLMService:
    return LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=StubChat(),
    )


@pytest.mark.asyncio
async def test_retrieve_pre_joins_batch():
    svc = _svc()
    q = await svc.retrieve_pre(["hi", "there"])
    assert "hi" in q and "there" in q


@pytest.mark.asyncio
async def test_retrieve_post_passthrough():
    svc = _svc()
    assert await svc.retrieve_post("q", ["a", "b"]) == ["a", "b"]


@pytest.mark.asyncio
async def test_summarize_includes_old_and_new():
    svc = _svc()
    out = await svc.summarize("old", ["new1", "new2"], max_chars=1000)
    assert "old" in out and "new1" in out


@pytest.mark.asyncio
async def test_cluster_topics_calls_chat():
    class Capture(StubChat):
        async def complete(self, system, user):
            assert "topic blocks" in system
            return '[{"topic": "Hi", "ids": [1], "kind": "topic"}]'

    svc = LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=Capture(),
    )
    raw = await svc.cluster_topics("1|User|hello")
    assert "Hi" in raw


@pytest.mark.asyncio
async def test_embed_uses_role():
    svc = _svc()
    vecs = await svc.embed(["hello"], role="query")
    assert len(vecs[0]) == EMBEDDING_DIM
