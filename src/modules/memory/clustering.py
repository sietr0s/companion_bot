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


def _load_topic_array(text: str) -> list | None:
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


MIN_TOPIC_MESSAGES = 2


def _contiguous_runs(seqs: list[int]) -> list[list[int]]:
    if not seqs:
        return []
    ordered = sorted(set(seqs))
    runs: list[list[int]] = [[ordered[0]]]
    for seq in ordered[1:]:
        if seq == runs[-1][-1] + 1:
            runs[-1].append(seq)
        else:
            runs.append([seq])
    return runs


def normalize_cluster_blocks(
    blocks: list[TopicBlock],
    window_seqs: list[int],
) -> list[TopicBlock] | None:
    """Drop 1-message topics, overlapping noise, and fill leftover ids as noise."""
    if not blocks or not window_seqs:
        return None
    window = set(window_seqs)
    occupied: set[int] = set()
    normalized: list[TopicBlock] = []
    for block in blocks:
        ids = [seq for seq in block.ids if seq in window and seq not in occupied]
        if not ids:
            continue
        kind = block.kind
        if kind == "topic" and len(ids) < MIN_TOPIC_MESSAGES:
            kind = "noise"
        for run in _contiguous_runs(ids):
            run_kind = "noise" if kind == "topic" and len(run) < MIN_TOPIC_MESSAGES else kind
            normalized.append(TopicBlock(block.topic, run, run_kind))
            occupied.update(run)
    leftovers = [seq for seq in window_seqs if seq not in occupied]
    for run in _contiguous_runs(leftovers):
        normalized.append(TopicBlock("noise", run, "noise"))
    if not normalized:
        return None
    order = {seq: i for i, seq in enumerate(window_seqs)}
    normalized.sort(key=lambda block: order.get(block.ids[0], 0))
    return normalized


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
    if open_blocks[0].kind == "noise":
        return list(blocks), []
    return closed, list(open_blocks[0].ids)
