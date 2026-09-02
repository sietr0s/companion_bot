"""Deterministic chat stub for tests and missing API keys."""


class StubChat:
    async def complete(self, system: str, user: str) -> str:
        text = user.strip()
        system_l = system.lower()
        if "search query" in system_l:
            return text
        if "relevant snippets" in system_l:
            return "\n".join(
                line.strip("- ").strip()
                for line in text.splitlines()
                if line.startswith("- ")
            )
        if "сводка" in text.lower():
            return text
        last_line = text.splitlines()[-1] if text else ""
        return f"Got it: {last_line}"
