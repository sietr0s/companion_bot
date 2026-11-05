"""Text and model-response utilities specific to memory; no ORM or service dependencies."""

from __future__ import annotations

import json
import re

from src.modules.memory.domain import HistoryMessage, TopicBlock

_LABELS = {"incoming": "User", "outgoing": "Assistant"}
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _unwrap_content(raw: str) -> str:
    text = _FENCE.sub("", (raw or "").strip())
    try:
        outer = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(outer, list) and outer and isinstance(outer[0], dict) and "text" in outer[0]:
        return _unwrap_content(str(outer[0].get("text") or ""))
    if isinstance(outer, dict) and "text" in outer and "ids" not in outer:
        return _unwrap_content(str(outer.get("text") or ""))
    return text


def _load_topic_array(text: str) -> list[object] | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "[":
            continue
        try:
            data, _end = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, list) or not data:
            continue
        if isinstance(data[0], dict) and ("ids" in data[0] or "topic" in data[0]):
            return data
    return None


def parse_cluster_json(raw: str) -> list[TopicBlock] | None:
    data = _load_topic_array(_unwrap_content(raw))
    if data is None:
        return None
    blocks: list[TopicBlock] = []
    for item in data:
        if not isinstance(item, dict):
            return None
        kind = str(item.get("kind") or "topic").strip().lower() or "topic"
        topic = str(item.get("topic") or "").strip() or kind
        ids = item.get("ids")
        if not isinstance(ids, list) or not ids:
            return None
        if kind not in {"topic", "noise"}:
            return None
        try:
            seqs = [int(x) for x in ids]
        except (TypeError, ValueError):
            return None
        blocks.append(TopicBlock(topic=topic, ids=seqs, kind=kind))
    return blocks


def retrieve_pre_input(
    recent: list[tuple[str, str]],
    limit: int,
) -> tuple[list[str], str]:
    """Last `limit` turns as User/Assistant lines; fallback is last incoming texts."""
    window = recent[-limit:] if limit > 0 else list(recent)
    lines = [f"{_LABELS[direction]}: {text}" for direction, text in window]
    last_user = [text for direction, text in window if direction == "incoming"]
    fallback = (last_user[-1] if last_user else " ".join(text for _, text in window)).strip()
    return lines, fallback


def numbered_window(messages: list[HistoryMessage]) -> str:
    """ORM messages: sequence_number|User|text."""
    lines = []
    for msg in messages:
        label = _LABELS[msg.direction]
        lines.append(f"{msg.sequence_number}|{label}|{msg.text}")
    return "\n".join(lines)


def topic_embed_text(
    title: str,
    messages: list[tuple[str, str]],
    *,
    max_chars: int,
) -> str:
    body = "\n".join(f"{_LABELS[direction]}: {text}" for direction, text in messages)
    if max_chars > 0 and len(body) > max_chars:
        body = body[:max_chars].rstrip()
    title = (title or "").strip()
    if not body:
        return title
    if not title:
        return body
    return f"{title}\n{body}"
