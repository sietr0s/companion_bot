"""LLM-generated clusters must never lose or duplicate messages during normalization."""

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from src.modules.memory.domain import (
    TopicBlock,
    normalize_cluster_blocks,
    split_closed_open,
)
from src.modules.memory.utils import parse_cluster_json


@st.composite
def cluster_windows(draw):
    length = draw(st.integers(min_value=1, max_value=50))
    start = draw(st.integers(min_value=1, max_value=10000))
    window = list(range(start, start + length))
    groups = draw(
        st.lists(
            st.tuples(
                st.lists(st.integers(start - 5, start + length + 5), min_size=1, max_size=60),
                st.sampled_from(["topic", "noise"]),
            ),
            min_size=1,
            max_size=10,
        )
    )
    return window, [TopicBlock("topic", ids, kind) for ids, kind in groups]


@given(cluster_windows())
@settings(max_examples=150)
def test_normalization_partitions_the_entire_window_once(case):
    window, blocks = case
    normalized = normalize_cluster_blocks(blocks, window)
    assert normalized is not None
    ids = [seq for block in normalized for seq in block.ids]
    assert sorted(ids) == window
    assert len(ids) == len(set(ids))
    assert all(block.ids == list(range(block.ids[0], block.ids[-1] + 1)) for block in normalized)
    assert all(len(block.ids) >= 2 for block in normalized if block.kind == "topic")
    hard = split_closed_open(normalized, window, hard_cap=True)
    assert hard == (normalized, [])
    soft = split_closed_open(normalized, window, hard_cap=False)
    assert soft is not None
    closed, open_ids = soft
    assert sorted([seq for block in closed for seq in block.ids] + open_ids) == window
    if open_ids:
        assert open_ids[-1] == window[-1]


@given(st.text(max_size=2000))
def test_parser_handles_arbitrary_model_text(raw):
    result = parse_cluster_json(raw)
    assert result is None or all(block.ids and block.kind in {"noise", "topic"} for block in result)


@given(st.lists(st.integers(min_value=1, max_value=1000), min_size=1, max_size=50))
def test_parser_preserves_numeric_message_ids(ids):
    raw = json.dumps([{"topic": "тема", "ids": ids, "kind": "topic"}], ensure_ascii=False)
    assert parse_cluster_json(raw) == [TopicBlock("тема", ids)]
