"""Public HTTP for Instagram accounts, settings, whitelist (admin JWT)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_account(api_client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = await api_client.post(
        "/api/v1/public/instagram/accounts/",
        json={"username": "x"},
        headers=headers,
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["username"] == "x"
    assert "password" not in body
    assert body["is_connected"] is False
    assert body["session_file"]
    assert "instagram" in body["session_file"]


@pytest.mark.asyncio
async def test_whitelist_add_and_remove(api_client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    created = await api_client.post(
        "/api/v1/public/instagram/accounts/",
        json={"username": "bot"},
        headers=headers,
    )
    assert created.status_code in (200, 201), created.text
    account_id = created.json()["id"]
    added = await api_client.post(
        f"/api/v1/public/instagram/{account_id}/whitelist",
        json={"user_pk": 101},
        headers=headers,
    )
    assert added.status_code == 200, added.text
    assert 101 in (added.json()["whitelist_user_pks"] or [])
    removed = await api_client.delete(
        f"/api/v1/public/instagram/{account_id}/whitelist/101",
        headers=headers,
    )
    assert removed.status_code == 200, removed.text
    assert 101 not in (removed.json()["whitelist_user_pks"] or [])
