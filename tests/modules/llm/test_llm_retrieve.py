import pytest

from src.bus.in_memory.producer import InMemoryProducer
from src.bus.in_memory.transport import InMemoryTransport
from src.modules.llm.service import LLMService
from src.modules.memory.constants import EMBEDDING_DIM


class FakeEmbedder:
    def embed(self, texts, *, role):
        assert role in ("query", "document")
        return [[float(len(role))] * EMBEDDING_DIM for _ in texts]


def _svc() -> LLMService:
    return LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
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
async def test_embed_uses_role():
    svc = _svc()
    vecs = await svc.embed(["hello"], role="query")
    assert len(vecs[0]) == EMBEDDING_DIM
