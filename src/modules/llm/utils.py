"""Translate shared chat entities to provider messages and memory prompts."""

from src.domain.chat import NEXT_MESSAGE_TAG, Batch, Topic, display_text


def _turns(batches: list[Batch]) -> list[tuple[str, str]]:
    turns: list[tuple[str, str]] = []
    for batch in batches:
        texts = [display_text(message) for message in batch.messages]
        text = NEXT_MESSAGE_TAG.join(value for value in texts if value)
        if not text:
            continue
        role = "ai" if batch.direction == "outgoing" else "human"
        if turns and turns[-1][0] == role:
            turns[-1] = (role, NEXT_MESSAGE_TAG.join([turns[-1][1], text]))
        else:
            turns.append((role, text))
    return turns


def batches_to_turns(batches: list[Batch]) -> list[tuple[str, str]]:
    turns = _turns(batches)
    if turns and turns[0][0] == "ai":
        turns = turns[1:]
    return turns


def format_topic(topic: Topic) -> str:
    lines = [topic.title]
    for role, text in _turns(topic.batches):
        lines.append(f"{'Assistant' if role == 'ai' else 'User'}: {text}")
    return "\n".join(lines)


def memory_system_suffix(
    summary: str | None, retrieved: list[Topic], references: list[Topic]
) -> str:
    sections: list[str] = []
    if summary:
        sections.append(f"Summary:\n{summary}")
    if retrieved:
        sections.append(
            "Earlier conversation topics:\n" + "\n\n".join(map(format_topic, retrieved))
        )
    if references:
        sections.append(
            "Reference examples (не текущий диалог):\n" + "\n\n".join(map(format_topic, references))
        )
    return "\n\n".join(sections)


_MAX_QUERY_CHARS = 160
_MAX_QUERY_WORDS = 16


def sanitize_search_query(raw: str, *, fallback: str) -> str:
    compact_fallback = " ".join((fallback or "").split())[:_MAX_QUERY_CHARS].strip()
    text = (raw or "").strip().strip("\"'")
    if text.lower().startswith("query:"):
        text = text[6:].strip()
    text = " ".join(text.split())
    words = text.split()
    sentences = [
        part for part in text.replace("!", ".").replace("?", ".").split(".") if part.strip()
    ]
    if (
        not text
        or len(text) > _MAX_QUERY_CHARS
        or len(words) > _MAX_QUERY_WORDS
        or len(sentences) > 1
    ):
        return compact_fallback
    return text
