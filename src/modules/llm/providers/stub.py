"""Deterministic chat stub for tests and missing API keys."""

from src.modules.llm.presets import DEFAULT_PRESETS
from src.modules.llm.providers.invoke import resolve_preset


class StubChat:
    async def complete(self, system: str, user: str, *, preset: str) -> str:
        return await self.complete_messages([("system", system), ("human", user)], preset=preset)

    async def complete_messages(self, messages: list[tuple[str, str]], *, preset: str) -> str:
        resolve_preset(DEFAULT_PRESETS, preset)
        system = next((t for r, t in messages if r == "system"), "")
        user_parts = [t for r, t in messages if r == "human"]
        text = user_parts[-1].strip() if user_parts else ""
        system_l = system.lower()
        if "search query" in system_l:
            return text
        if "relevant snippets" in system_l:
            return "\n".join(
                line.strip("- ").strip() for line in text.splitlines() if line.startswith("- ")
            )
        if "сводка" in text.lower():
            return text
        last_line = text.splitlines()[-1] if text else ""
        return f"Got it: {last_line}"
