from src.modules.memory.constants import EMBEDDING_DIM


class FakeEmbedder:
    def preload(self) -> None:
        return None

    def embed(self, texts, *, role):
        assert role in ("query", "document")
        return [[float(len(role))] * EMBEDDING_DIM for _ in texts]
