from typing import Protocol


class TtsProvider(Protocol):
    async def synthesize(self, text: str) -> bytes | None: ...
