from uuid import uuid4

from src.domain.chat import (
    Batch,
    ChatRef,
    ConversationContext,
    Message,
    Person,
    QuotedMessage,
    Topic,
    display_text,
    outgoing_batch,
    split_agent_text,
)


def test_message_and_batch_defaults():
    msg = Message(text="hi", reply_to=QuotedMessage(sender_name="Alice", text="план"))
    batch = Batch(channel="telegram", chat_id=1, account_id=uuid4(), messages=[msg])
    assert batch.messages[0].message_type == "text"
    assert batch.messages[0].direction == "incoming"
    assert batch.messages[0].reply_to.sender_name == "Alice"


def test_split_agent_text_on_next_message():
    assert split_agent_text("Хаха<next_message>Ты серьёзно?") == ["Хаха", "Ты серьёзно?"]
    assert split_agent_text("  one </next_message> two  ") == ["one", "two"]
    assert split_agent_text("   ") == []


def test_outgoing_batch_builds_messages():
    batch = outgoing_batch(
        channel="telegram",
        chat_id=7,
        account_id=uuid4(),
        text="a<next_message>b",
    )
    assert batch.channel == "telegram"
    assert [m.text for m in batch.messages] == ["a", "b"]
    assert all(m.direction == "outgoing" for m in batch.messages)


def test_display_text_marks_reply_and_forward():
    msg = Message(
        text="ок",
        reply_to=QuotedMessage(sender_name="Alice", text="план"),
        forward_from=QuotedMessage(sender_name="Bob"),
    )
    line = display_text(msg)
    assert '[reply to Alice: "план"]' in line
    assert "[forwarded from Bob]" in line
    assert line.endswith("ок")
    assert display_text(Message(text="просто")) == "просто"


def test_chat_ref_from_payload_requires_channel():
    aid = uuid4()
    ref = ChatRef.from_payload({"channel": "telegram", "account_id": aid, "chat_id": 9})
    assert ref.channel == "telegram"
    assert ref.chat_id == 9
    assert ref.adapter_ids()["chat_id"] == 9
    merged = ref.merged(ChatRef(channel="telegram", chat_id=9, conversation_id=uuid4()))
    assert merged.conversation_id is not None
    assert merged.account_id == ref.account_id
    try:
        ChatRef.from_payload({"account_id": aid, "chat_id": 9})
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_chat_ref_state_key_includes_channel():
    aid = uuid4()
    tg = ChatRef(channel="telegram", account_id=aid, chat_id=1)
    ig = ChatRef(channel="instagram", account_id=aid, chat_id=1)
    assert tg.state_key() != ig.state_key()


def test_conversation_context_from_payload():
    ctx = ConversationContext.from_payload(
        {
            "summary": "s",
            "recent": [
                {
                    "channel": "telegram",
                    "chat_id": 1,
                    "messages": [{"direction": "incoming", "text": "hi"}],
                }
            ],
        }
    )
    assert ctx.summary == "s"
    assert ctx.recent_messages()[0].text == "hi"
    topic = Topic(title="t", batches=[])
    ctx_ref = ConversationContext(references=[topic])
    assert ctx_ref.references[0].title == "t"


def test_person_display_name():
    assert Person(first_name="Ann", last_name="Lee").display_name == "Ann Lee"
    assert Person(username="ann").display_name == "ann"
