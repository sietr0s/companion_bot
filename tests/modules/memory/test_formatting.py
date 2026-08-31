from src.modules.memory.formatting import glue_batch, assemble_context


def test_glue_incoming():
    assert glue_batch(["a", "b"], "incoming") == "User: a\nUser: b"


def test_assemble_all_parts():
    text = assemble_context(
        summary="s",
        retrieved=["old batch"],
        recent=[("incoming", "hi"), ("outgoing", "yo")],
    )
    assert "Summary: s" in text
    assert "Retrieved:" in text and "old batch" in text
    assert "User: hi" in text and "Assistant: yo" in text


def test_assemble_omits_empty_retrieved():
    text = assemble_context(summary=None, retrieved=[], recent=[("incoming", "x")])
    assert "Retrieved" not in text
    assert "Summary" not in text
    assert "User: x" in text
