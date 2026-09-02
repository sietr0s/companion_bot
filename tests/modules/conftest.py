"""Autouse fakes for module tests so Qwen weights are never downloaded."""

import pytest

from tests.fakes.embedder import FakeEmbedder


@pytest.fixture(autouse=True)
def _fake_embedder(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeEmbedder()
    monkeypatch.setattr("src.modules.llm.dependencies._embedder", fake)
    monkeypatch.setattr("src.modules.llm.dependencies.get_embedder", lambda: fake)
    monkeypatch.setattr("src.modules.llm.handlers.get_embedder", lambda: fake)

    def _fake_embed(self, texts, *, role):
        return fake.embed(texts, role=role)

    monkeypatch.setattr("src.modules.llm.embedder.QwenEmbedder.embed", _fake_embed)
