"""STT provider protocol."""

from pathlib import Path
from typing import Protocol


class SttProvider(Protocol):
    def transcribe(self, path: Path) -> str: ...

    def preload(self) -> None: ...
