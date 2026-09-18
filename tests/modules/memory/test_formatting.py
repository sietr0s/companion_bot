from src.modules.memory.formatting import (
    format_topic_snippet,
    glue_batch,
    retrieve_pre_input,
    topic_embed_text,
)


def test_glue_incoming():
    assert glue_batch(["a", "b"], "incoming") == "User: a\nUser: b"


def test_glue_incoming_message_objects():
    from src.modules.memory.schemas.events import IncomingMessage

    assert (
        glue_batch(
            [IncomingMessage(text="a"), IncomingMessage(text="b")],
            "incoming",
        )
        == "User: a\nUser: b"
    )


def test_glue_reply_message():
    from src.domain.chat import QuotedMessage
    from src.modules.memory.schemas.events import IncomingMessage

    glued = glue_batch(
        [
            IncomingMessage(
                text="ок",
                reply_to=QuotedMessage(sender_name="Alice", text="план"),
            )
        ],
        "incoming",
    )
    assert '[reply to Alice: "план"] ок' in glued


def test_retrieve_pre_input_window_and_last_user_fallback():
    lines, fallback = retrieve_pre_input(
        [
            ("incoming", "привет"),
            ("outgoing", "хай"),
            ("incoming", "как дела"),
            ("outgoing", "норм"),
            ("incoming", "девушка ушла"),
        ],
        limit=4,
    )
    assert "привет" not in lines
    assert "User: как дела" in lines
    assert "Assistant: норм" in lines
    assert "User: девушка ушла" in lines
    assert fallback == "девушка ушла"


def test_topic_embed_text_joins_title_and_body():
    text = topic_embed_text(
        "сервер",
        [("incoming", "упал"), ("outgoing", "смотрю")],
        max_chars=400,
    )
    assert text.startswith("сервер")
    assert "User: упал" in text
    assert "Assistant: смотрю" in text


def test_format_topic_snippet_caps_and_ellipsis():
    msgs = [("incoming", f"m{i}") for i in range(5)]
    text = format_topic_snippet("тема", msgs, max_messages=2)
    assert text.startswith("тема")
    assert "…" in text
    assert "m3" in text and "m4" in text
    assert "m0" not in text
