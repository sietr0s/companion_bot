import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.bus.in_memory.producer import InMemoryProducer
from src.bus.in_memory.transport import InMemoryTransport
from src.modules.llm import dependencies as llm_deps
from src.modules.llm.dependencies import build_chat_provider
from src.modules.llm.providers.mistral import MistralChat
from src.modules.llm.providers.openai_compat import OPENROUTER_BASE_URL, OpenAICompatChat
from src.modules.llm.providers.stub import StubChat
from src.modules.llm.schemas.events import GenerateReplyCommand
from src.modules.llm.service import LLMService
from tests.fakes.embedder import FakeEmbedder


@pytest.mark.asyncio
async def test_mistral_complete_uses_ainvoke(monkeypatch):
    llm = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content="  hi  ")))
    monkeypatch.setattr(
        "src.modules.llm.providers.mistral.ChatMistralAI",
        lambda **kwargs: llm,
    )
    chat = MistralChat(api_key="key", model="mistral-small-latest")
    assert await chat.complete("sys", "user") == "hi"
    llm.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_warmup_calls_embedder_preload(monkeypatch):
    from src.modules.llm import dependencies as llm_deps

    class PreloadEmbedder:
        def __init__(self):
            self.called = False

        def preload(self):
            self.called = True

    fake = PreloadEmbedder()
    monkeypatch.setattr(llm_deps, "get_embedder", lambda: fake)
    monkeypatch.setattr(llm_deps, "get_chat_provider", lambda: StubChat())
    await llm_deps.warmup_heavy_models()
    assert fake.called is True


def test_build_chat_requires_mistral_key(monkeypatch):
    monkeypatch.setattr(
        llm_deps,
        "settings",
        SimpleNamespace(
            LLM_PROVIDER="mistral", MISTRAL_API_KEY="", MISTRAL_MODEL="mistral-small-latest"
        ),
    )
    with pytest.raises(RuntimeError, match="MISTRAL_API_KEY"):
        build_chat_provider()


def test_build_chat_stub_when_requested(monkeypatch):
    monkeypatch.setattr(llm_deps, "settings", SimpleNamespace(LLM_PROVIDER="stub"))
    assert isinstance(build_chat_provider(), StubChat)


def test_build_chat_requires_openrouter_key(monkeypatch):
    monkeypatch.setattr(
        llm_deps,
        "settings",
        SimpleNamespace(LLM_PROVIDER="openrouter", LLM_API_KEY="", LLM_BASE_URL="", LLM_MODEL="x"),
    )
    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        build_chat_provider()


def test_build_chat_mistral_when_key_set(monkeypatch):
    monkeypatch.setattr(
        llm_deps,
        "settings",
        SimpleNamespace(
            LLM_PROVIDER="mistral",
            MISTRAL_API_KEY="sk-test",
            MISTRAL_MODEL="mistral-small-latest",
        ),
    )
    monkeypatch.setattr(
        "src.modules.llm.providers.mistral.ChatMistralAI",
        lambda **kwargs: SimpleNamespace(),
    )
    assert isinstance(build_chat_provider(), MistralChat)


def test_build_chat_openrouter_when_key_set(monkeypatch):
    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr(
        llm_deps,
        "settings",
        SimpleNamespace(
            LLM_PROVIDER="openrouter",
            LLM_API_KEY="or-key",
            LLM_BASE_URL="",
            LLM_MODEL="openai/gpt-4o-mini",
        ),
    )
    monkeypatch.setattr(
        "src.modules.llm.providers.openai_compat.ChatOpenAI",
        fake_chat_openai,
    )
    chat = build_chat_provider()
    assert isinstance(chat, OpenAICompatChat)
    assert captured["base_url"] == OPENROUTER_BASE_URL
    assert captured["model"] == "openai/gpt-4o-mini"


@pytest.mark.asyncio
async def test_openai_compat_complete_uses_ainvoke(monkeypatch):
    llm = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content="  hi  ")))
    monkeypatch.setattr(
        "src.modules.llm.providers.openai_compat.ChatOpenAI",
        lambda **kwargs: llm,
    )
    chat = OpenAICompatChat(api_key="k", model="m", base_url="https://openrouter.ai/api/v1")
    assert await chat.complete("sys", "user") == "hi"
    llm.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_reply_uses_chat():
    chat = StubChat()
    svc = LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=chat,
    )
    event = await svc.generate_reply(
        GenerateReplyCommand(
            conversation_id=uuid.uuid4(),
            channel="telegram",
            chat_id=1,
            recent=[
                {
                    "channel": "telegram",
                    "chat_id": 1,
                    "messages": [{"direction": "incoming", "text": "hello"}],
                }
            ],
        )
    )
    assert [m.text for m in event.messages] == ["Got it: hello"]
    assert event.batch is not None
    assert event.batch.messages[0].direction == "outgoing"


@pytest.mark.asyncio
async def test_generate_reply_splits_next_message():
    class MultiChat:
        async def complete(self, system, user):
            return "Хаха<next_message>Ты серьёзно?"

        async def complete_messages(self, messages):
            return "Хаха<next_message>Ты серьёзно?"

    svc = LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=MultiChat(),
    )
    event = await svc.generate_reply(
        GenerateReplyCommand(
            conversation_id=uuid.uuid4(),
            channel="telegram",
            chat_id=1,
            recent=[
                {
                    "channel": "telegram",
                    "chat_id": 1,
                    "messages": [{"direction": "incoming", "text": "hi"}],
                }
            ],
        )
    )
    assert [m.text for m in event.messages] == ["Хаха", "Ты серьёзно?"]
    assert len(event.batch.messages) == 2


@pytest.mark.asyncio
async def test_generate_reply_sends_chat_roles_not_one_human_blob():
    class CaptureChat:
        def __init__(self):
            self.messages = None

        async def complete(self, system, user):
            raise AssertionError("reply must use complete_messages")

        async def complete_messages(self, messages):
            self.messages = messages
            return "ок"

    chat = CaptureChat()
    svc = LLMService(
        message_bus=InMemoryProducer(InMemoryTransport()),
        embedder=FakeEmbedder(),
        chat=chat,
    )
    await svc.generate_reply(
        GenerateReplyCommand(
            conversation_id=uuid.uuid4(),
            channel="telegram",
            chat_id=1,
            summary="диалог про приветы",
            retrieved=[
                {
                    "title": "макароны",
                    "batches": [
                        {
                            "channel": "telegram",
                    "chat_id": 1,
                            "messages": [{"direction": "incoming", "text": "потетим"}],
                        }
                    ],
                }
            ],
            references=[
                {
                    "title": "стиль",
                    "kind": "reference",
                    "batches": [
                        {
                            "channel": "telegram",
                    "chat_id": 1,
                            "messages": [{"direction": "incoming", "text": "скучно"}],
                        },
                        {
                            "channel": "telegram",
                    "chat_id": 1,
                            "messages": [{"direction": "outgoing", "text": "пойдём гулять"}],
                        },
                    ],
                }
            ],
            recent=[
                {
                    "channel": "telegram",
                    "chat_id": 1,
                    "messages": [{"direction": "incoming", "text": "макароны"}],
                },
                {
                    "channel": "telegram",
                    "chat_id": 1,
                    "messages": [{"direction": "outgoing", "text": "не пробовала"}],
                },
                {
                    "channel": "telegram",
                    "chat_id": 1,
                    "messages": [{"direction": "incoming", "text": "а 100к скидывать?"}],
                },
            ],
        )
    )
    roles = [r for r, _ in chat.messages]
    assert roles[0] == "system"
    assert "диалог про приветы" in chat.messages[0][1]
    assert "макароны" in chat.messages[0][1]
    assert "не текущий диалог" in chat.messages[0][1].lower()
    assert "гулять" in chat.messages[0][1]
    assert roles[1:] == ["human", "ai", "human"]
    assert chat.messages[-1] == ("human", "а 100к скидывать?")
    assert not any(r == "human" and "Summary:" in t for r, t in chat.messages)
