"""Shared LangChain chat invocation."""

from src.modules.llm.presets import SamplingPreset


def message_text(message) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, list):
        return content[0]["text"].strip()
    if isinstance(content, str):
        return content.strip()
    return str(content).strip()


def resolve_preset(presets: dict[str, SamplingPreset], name: str) -> SamplingPreset:
    try:
        return presets[name]
    except KeyError as exc:
        raise ValueError(f"unknown llm preset: {name}") from exc


def bind_preset(llm, preset: SamplingPreset):
    return llm.bind(
        temperature=preset.temperature,
        top_p=preset.top_p,
        max_tokens=preset.max_tokens,
    )


async def acomplete(llm, system: str, user: str, preset: SamplingPreset) -> str:
    return await acomplete_messages(llm, [("system", system), ("human", user)], preset)


async def acomplete_messages(llm, messages: list[tuple[str, str]], preset: SamplingPreset) -> str:
    message = await bind_preset(llm, preset).ainvoke(list(messages))
    return message_text(message)
