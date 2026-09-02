"""Shared LangChain chat invocation."""


def message_text(message) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content.strip()
    return str(content).strip()


async def acomplete(llm, system: str, user: str) -> str:
    message = await llm.ainvoke(
        [
            ("system", system),
            ("human", user),
        ]
    )
    return message_text(message)
