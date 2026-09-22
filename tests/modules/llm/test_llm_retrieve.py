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
    class Recording(StubChat):
        def __init__(self):
            self.preset = None

        async def complete(self, system, user, *, preset: str):
            self.preset = preset
            return await super().complete(system, user, preset=preset)

    chat = Recording()
    svc = LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=chat,
    )
    q = await svc.retrieve_pre(["hi", "there"])
    assert "hi" in q and "there" in q
    assert chat.preset == "rag"


@pytest.mark.asyncio
async def test_retrieve_pre_falls_back_when_model_replies():
    class Chatty:
        async def complete(self, system, user, *, preset: str):
            return (
                "Я тебя слышу — похоже, ты в растерянности.\n\n"
                "Расскажи подробнее, и я постараюсь помочь."
            )

    svc = LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=Chatty(),
    )
    q = await svc.retrieve_pre(
        [
            "User: привет",
            "Assistant: хай",
            "User: Можешь представить, моя девушка пошла как-нибудь, как мне на это реагировать",
        ],
        fallback="Можешь представить, моя девушка пошла как-нибудь, как мне на это реагировать",
    )
    assert "девушк" in q.lower()
    assert "я тебя слышу" not in q.lower()
    assert "привет" not in q.lower()
    assert "\n\n" not in q


@pytest.mark.asyncio
async def test_retrieve_post_uses_user_not_duplicated_prompt():
    class Capture:
        def __init__(self):
            self.system = None
            self.user = None

        async def complete(self, system, user, *, preset: str):
            self.system = system
            self.user = user
            return "a"

    chat = Capture()
    svc = LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=chat,
    )
    assert await svc.retrieve_post("ссора с девушкой", ["a", "b"]) == ["a"]
    assert chat.system != chat.user
    assert "ссора с девушкой" in chat.user
    assert "ссора с девушкой" not in chat.system


@pytest.mark.asyncio
async def test_retrieve_post_passthrough():
    class Recording(StubChat):
        def __init__(self):
            self.preset = None

        async def complete(self, system, user, *, preset: str):
            self.preset = preset
            return await super().complete(system, user, preset=preset)

    chat = Recording()
    svc = LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=chat,
    )
    assert await svc.retrieve_post("q", ["a", "b"]) == ["a", "b"]
    assert chat.preset == "rag"


@pytest.mark.asyncio
async def test_retrieve_post_empty_keeps_none():
    class Silent:
        async def complete(self, system, user, *, preset: str):
            return "none of these"

    svc = LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=Silent(),
    )
    assert await svc.retrieve_post("q", ["alpha", "beta"]) == []


@pytest.mark.asyncio
async def test_retrieve_post_exact_match_only():
    class Substring:
        async def complete(self, system, user, *, preset: str):
            return "plan"

    svc = LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=Substring(),
    )
    assert await svc.retrieve_post("q", ["weekend plans in berlin"]) == []


@pytest.mark.asyncio
async def test_summarize_includes_old_and_new():
    class Recording(StubChat):
        def __init__(self):
            self.preset = None

        async def complete(self, system, user, *, preset: str):
            self.preset = preset
            return await super().complete(system, user, preset=preset)

    chat = Recording()
    svc = LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=chat,
    )
    out = await svc.summarize("old", ["new1", "new2"], max_chars=1000)
    assert "old" in out and "new1" in out
    assert chat.preset == "extract"


@pytest.mark.asyncio
async def test_cluster_topics_calls_chat():
    class Capture(StubChat):
        async def complete(self, system, user, *, preset: str):
            self.preset = preset
            assert "topic blocks" in system
            return '[{"topic": "Hi", "ids": [1], "kind": "topic"}]'

    chat = Capture()
    svc = LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=chat,
    )
    raw = await svc.cluster_topics("1|User|hello")
    assert "Hi" in raw
    assert chat.preset == "extract"


@pytest.mark.asyncio
async def test_embed_uses_role():
    svc = _svc()
    vecs = await svc.embed(["hello"], role="query")
    assert len(vecs[0]) == EMBEDDING_DIM
