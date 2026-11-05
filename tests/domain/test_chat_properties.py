"""Chat identity and reply boundaries across arbitrary account/channel inputs."""

from hypothesis import given
from hypothesis import strategies as st

from src.domain.chat import ChatRef, outgoing_batch, split_agent_text


@given(st.uuids(), st.integers(min_value=-(2**53), max_value=2**53))
def test_identity_round_trip_keeps_channel_and_account(account_id, chat_id):
    telegram = ChatRef(channel="telegram", account_id=account_id, chat_id=chat_id)
    instagram = ChatRef(channel="instagram", account_id=account_id, chat_id=chat_id)
    assert telegram.state_key() != instagram.state_key()
    assert ChatRef.from_payload(telegram.bus_ids()) == telegram


@given(
    st.lists(
        st.text(alphabet=st.characters(blacklist_characters="<>"), max_size=100).filter(
            lambda value: bool(value.strip())
        ),
        min_size=1,
        max_size=10,
    )
)
def test_reply_split_and_batch_keep_nonempty_bubbles(parts):
    expected = [part.strip() for part in parts]
    content = "<next_message>".join(parts)
    assert split_agent_text(content) == expected
    batch = outgoing_batch(channel="telegram", chat_id=1, account_id=None, text=content)
    assert [message.text for message in batch.messages] == expected
    assert all(message.direction == "outgoing" for message in batch.messages)
