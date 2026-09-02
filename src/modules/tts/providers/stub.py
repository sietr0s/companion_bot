class StubTts:
    async def synthesize(self, text: str) -> bytes | None:
        return None
