from src.domain.chat import Batch, Message, Topic
from src.modules.llm.formatting import batches_to_turns, format_topic, memory_system_suffix


def test_batches_to_turns_joins_bubbles_with_next_message():
    turns = batches_to_turns(
        [
            Batch(
                channel="telegram", chat_id=1,
                messages=[Message(text="hi", direction="outgoing")],
            ),
            Batch(
                channel="telegram", chat_id=1,
                messages=[
                    Message(text="макароны", direction="incoming"),
                    Message(text="100к", direction="incoming"),
                ],
            ),
            Batch(
                channel="telegram", chat_id=1,
                messages=[Message(text="ок", direction="outgoing")],
            ),
        ]
    )
    assert turns == [
        ("human", "макароны<next_message>100к"),
        ("ai", "ок"),
    ]


def test_format_topic_title_and_role_lines():
    text = format_topic(
        Topic(
            title="сервер",
            batches=[
                Batch(
                    channel="telegram", chat_id=1,
                    messages=[
                        Message(text="упал", direction="incoming"),
                        Message(text="логи пустые", direction="incoming"),
                    ],
                ),
                Batch(
                    channel="telegram", chat_id=1,
                    messages=[Message(text="смотрю", direction="outgoing")],
                ),
            ],
        )
    )
    assert text == "сервер\nUser: упал<next_message>логи пустые\nAssistant: смотрю"


def test_memory_system_suffix_uses_topics():
    text = memory_system_suffix(
        "old story",
        [Topic(title="макароны", batches=[])],
        [Topic(title="стиль", kind="reference", batches=[])],
    )
    assert "old story" in text
    assert "макароны" in text
    assert "стиль" in text
    assert "не текущий диалог" in text.lower()
