from src.modules.memory.clustering import (
    TopicBlock,
    normalize_cluster_blocks,
    parse_cluster_json,
    split_closed_open,
)


def test_parse_extracts_array_from_prose():
    raw = 'Sure.\n[{"topic": "Погода", "ids": [1, 2], "kind": "topic"}]\n'
    blocks = parse_cluster_json(raw)
    assert blocks is not None
    assert blocks[0].topic == "Погода"
    assert blocks[0].ids == [1, 2]


def test_parse_skips_inner_ids_array_and_fences():
    raw = (
        "Example ids [1, 2, 3]\n```json\n"
        '[{"topic": "Погода", "ids": [10, 11], "kind": "topic"}]\n```'
    )
    blocks = parse_cluster_json(raw)
    assert blocks is not None
    assert blocks[0].ids == [10, 11]


def test_parse_wrapped_content_block():
    raw = (
        '[{"type":"text","text":"```json\\n'
        '[{\\"topic\\": \\"x\\", \\"ids\\": [1, 2], \\"kind\\": \\"topic\\"}]\\n```"}]'
    )
    blocks = parse_cluster_json(raw)
    assert blocks is not None
    assert blocks[0].ids == [1, 2]


def test_split_keeps_last_block_open():
    blocks = [
        TopicBlock("A", [1, 2], "topic"),
        TopicBlock("B", [3, 4], "topic"),
    ]
    closed, open_ids = split_closed_open(blocks, [1, 2, 3, 4], hard_cap=False)
    assert [b.topic for b in closed] == ["A"]
    assert open_ids == [3, 4]


def test_split_hard_cap_closes_all():
    blocks = [TopicBlock("A", [1, 2, 3], "topic")]
    closed, open_ids = split_closed_open(blocks, [1, 2, 3], hard_cap=True)
    assert len(closed) == 1
    assert open_ids == []


def test_split_rejects_overlap():
    blocks = [
        TopicBlock("A", [1, 2], "topic"),
        TopicBlock("B", [2, 3], "topic"),
    ]
    assert split_closed_open(blocks, [1, 2, 3], hard_cap=False) is None


def test_split_rejects_hole():
    blocks = [
        TopicBlock("A", [1], "topic"),
        TopicBlock("B", [3], "topic"),
    ]
    assert split_closed_open(blocks, [1, 2, 3], hard_cap=False) is None


def test_normalize_one_message_topic_becomes_noise():
    blocks = [
        TopicBlock("покупки на wildberries", [1, 2, 3], "topic"),
        TopicBlock("хах", [4], "topic"),
    ]
    out = normalize_cluster_blocks(blocks, [1, 2, 3, 4])
    kinds = [(b.kind, b.ids) for b in out]
    assert ("topic", [1, 2, 3]) in kinds
    assert ("noise", [4]) in kinds


def test_normalize_drops_overlapping_noise_and_fills_holes():
    blocks = [
        TopicBlock("домашние дела", [1, 2, 3], "topic"),
        TopicBlock("смех", [2], "noise"),
        TopicBlock("годовщина", [5, 6], "topic"),
    ]
    out = normalize_cluster_blocks(blocks, [1, 2, 3, 4, 5, 6])
    assert out is not None
    topics = [b for b in out if b.kind == "topic"]
    noise = [b for b in out if b.kind == "noise"]
    assert [b.ids for b in topics] == [[1, 2, 3], [5, 6]]
    assert [b.ids for b in noise] == [[4]]
    split = split_closed_open(out, [1, 2, 3, 4, 5, 6], hard_cap=True)
    assert split is not None
    closed, open_ids = split
    assert open_ids == []
    assert [b.kind for b in closed if b.kind == "topic"] == ["topic", "topic"]


def test_split_closes_trailing_noise():
    blocks = [
        TopicBlock("A", [1, 2], "topic"),
        TopicBlock("хах", [3], "noise"),
    ]
    closed, open_ids = split_closed_open(blocks, [1, 2, 3], hard_cap=False)
    assert open_ids == []
    assert [b.kind for b in closed] == ["topic", "noise"]
