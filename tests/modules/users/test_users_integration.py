"""Интеграция HTTP CRUD собеседников (только admin JWT)."""

import pytest
from httpx import AsyncClient


class TestUsersCRUD:
    @pytest.mark.asyncio
    async def test_admin_crud(
        self,
        api_client: AsyncClient,
        admin_token: str,
        auth_token: str,
    ) -> None:
        admin = {"Authorization": f"Bearer {admin_token}"}
        user_headers = {"Authorization": f"Bearer {auth_token}"}

        forbidden = await api_client.get("/api/v1/public/users/", headers=user_headers)
        assert forbidden.status_code == 403

        created = await api_client.post(
            "/api/v1/public/users/",
            json={
                "platform": "telegram",
                "platform_user_id": "10001",
                "first_name": "Alice",
                "notes": "коротко",
            },
            headers=admin,
        )
        assert created.status_code == 201, created.text
        body = created.json()
        user_id = body["id"]
        assert body["platform"] == "telegram"
        assert body["platform_user_id"] == "10001"
        assert body["notes"] == "коротко"

        listed = await api_client.get("/api/v1/public/users/", headers=admin)
        assert listed.status_code == 200
        assert listed.json()["total"] >= 1

        updated = await api_client.put(
            f"/api/v1/public/users/{user_id}",
            json={"first_name": "Alicia", "notes": "любит мемы"},
            headers=admin,
        )
        assert updated.status_code == 200
        assert updated.json()["first_name"] == "Alicia"

        deleted = await api_client.delete(
            f"/api/v1/public/users/{user_id}",
            headers=admin,
        )
        assert deleted.status_code == 204
