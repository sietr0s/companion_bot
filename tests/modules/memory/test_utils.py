from src.modules.memory.utils import (
    retrieve_pre_input,
    topic_embed_text,
)


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
