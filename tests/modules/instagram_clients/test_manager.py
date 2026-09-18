"""InstagramClientManager: injected client, no live Instagram."""

from uuid import uuid4

import pytest

from src.modules.instagram_clients.adapters.client_manager import InstagramClientManager
from src.modules.instagram_clients.dependencies import get_instagram_client_manager


class RecordingClient:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    def direct_send(self, text: str, thread_ids: list[int]) -> dict:
        self.sent.append((thread_ids[0], text))
        return {"id": "item-1"}


def test_get_instagram_client_manager_without_configure(monkeypatch):
    import src.modules.instagram_clients.dependencies as dep

    monkeypatch.setattr(dep, "_instagram_client_manager", None)
    with pytest.raises(RuntimeError, match="InstagramClientManager"):
        get_instagram_client_manager()


@pytest.mark.asyncio
async def test_manager_send_text_uses_injected_client():
    client = RecordingClient()
    mgr = InstagramClientManager(client_factory=lambda: client)
    aid = uuid4()
    mgr.attach(aid, client)
    item_id = await mgr.send_text(aid, thread_id=11, text="hi")
    assert item_id == "item-1"
    assert client.sent == [(11, "hi")]
