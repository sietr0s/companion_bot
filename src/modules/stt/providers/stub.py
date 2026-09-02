"""Deterministic STT stub for tests."""

from pathlib import Path


class StubStt:
    def transcribe(self, path: Path) -> str:
        return "transcribed"

    def preload(self) -> None:
        return None
