"""Parse and validate LLM topic-cluster JSON."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TopicBlock:
    topic: str
    ids: list[int]
    kind: str = "topic"


_ARRAY = re.compile(r"\[.*\]", re.DOTALL)


def parse_cluster_json(raw: str) -> list[TopicBlock] | None:
    match = _ARRAY.search(raw or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    blocks: list[TopicBlock] = []
    for item in data:
        if not isinstance(item, dict):
            return None
        topic = str(item.get("topic") or "").strip()
        ids = item.get("ids")
        kind = str(item.get("kind") or "topic").strip() or "topic"
        if not topic or not isinstance(ids, list) or not ids:
            return None
        if kind not in {"topic", "noise"}:
            return None
        try:
            seqs = [int(x) for x in ids]
        except (TypeError, ValueError):
            return None
        blocks.append(TopicBlock(topic=topic, ids=seqs, kind=kind))
    return blocks


def split_closed_open(
    blocks: list[TopicBlock],
    window_seqs: list[int],
    *,
    hard_cap: bool,
) -> tuple[list[TopicBlock], list[int]] | None:
    if not blocks or not window_seqs:
        return None
    window = list(window_seqs)
    occupied: set[int] = set()
    for block in blocks:
        if not block.ids:
            return None
        expected = list(range(block.ids[0], block.ids[-1] + 1))
        if block.ids != expected:
            return None
        for seq in block.ids:
            if seq not in window or seq in occupied:
                return None
            occupied.add(seq)
    if occupied != set(window):
        return None
    last = window[-1]
    if hard_cap:
        return list(blocks), []
    closed = [b for b in blocks if last not in b.ids]
    open_blocks = [b for b in blocks if last in b.ids]
    if len(open_blocks) != 1:
        return None
    return closed, list(open_blocks[0].ids)
