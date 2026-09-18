"""Direct inbox poll: seed cursor, skip own/old, whitelist."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.modules.instagram_clients.adapters.client_manager import InstagramClientManager


def _item(item_id: str, user_id: int, text: str = "hi") -> SimpleNamespace:
    return SimpleNamespace(id=item_id, user_id=user_id, text=text)


def _thread(thread_id: int, items: list) -> SimpleNamespace:
    return SimpleNamespace(id=thread_id, messages=items)


class InboxClient:
    def __init__(self, threads: list) -> None:
        self._threads = threads

    def direct_threads(self, amount: int = 20) -> list:
        return self._threads


@pytest.mark.asyncio
async def test_first_poll_seeds_cursor_without_emit():
    own_pk = 1
    client = InboxClient(
        [_thread(11, [_item("10", 2, "old"), _item("20", 2, "newer")])]
    )
    mgr = InstagramClientManager(client_factory=lambda: client)
    aid = uuid4()
    mgr.attach(aid, client)
    events, cursors = await mgr.poll_once(
        aid,
        own_pk=own_pk,
        use_whitelist=False,
        whitelist_user_pks=[],
        last_item_ids={},
    )
    assert events == []
    assert cursors[11] == "20"


@pytest.mark.asyncio
async def test_poll_once_emits_new_text_skips_own_and_old():
    own_pk = 1
    client = InboxClient(
        [
            _thread(
                11,
                [
                    _item("10", 2, "old"),
                    _item("20", 1, "mine"),
                    _item("30", 2, "hello"),
                ],
            )
        ]
    )
    mgr = InstagramClientManager(client_factory=lambda: client)
    aid = uuid4()
    mgr.attach(aid, client)
    events, cursors = await mgr.poll_once(
        aid,
        own_pk=own_pk,
        use_whitelist=False,
        whitelist_user_pks=[],
        last_item_ids={11: "10"},
    )
    assert [e.text for e in events] == ["hello"]
    assert events[0].chat_id == 11
    assert events[0].message_id == "30"
    assert events[0].sender.sender_id == 2
    assert events[0].channel == "instagram"
    assert cursors[11] == "30"


@pytest.mark.asyncio
async def test_poll_once_respects_whitelist():
    client = InboxClient(
        [
            _thread(11, [_item("2", 101, "ok")]),
            _thread(12, [_item("2", 999, "nope")]),
        ]
    )
    mgr = InstagramClientManager(client_factory=lambda: client)
    aid = uuid4()
    mgr.attach(aid, client)
    events, _ = await mgr.poll_once(
        aid,
        own_pk=1,
        use_whitelist=True,
        whitelist_user_pks=[101],
        last_item_ids={11: "1", 12: "1"},
    )
    assert [e.text for e in events] == ["ok"]
    assert events[0].sender.sender_id == 101
