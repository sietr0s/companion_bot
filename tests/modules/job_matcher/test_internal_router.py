"""Тест internal API подписок job_matcher."""

import uuid
from collections.abc import AsyncGenerator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.core.config import settings
from src.core.security import create_access_token
from src.main import app
from src.modules.job_matcher.repository import JobOfferRepository, SubscriptionRepository


async def test_get_subscriptions_for_admin_ui(db_session: AsyncSession) -> None:
    auth_id = uuid.uuid4()
    category_id = uuid.uuid4()
    subscription = await SubscriptionRepository().create(
        db_session,
        {
            "auth_id": auth_id,
            "category_ids": [str(category_id)],
            "keywords": ["python"],
            "locations": ["Удалённо"],
            "is_active": True,
        },
    )

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY},
        ) as client:
            response = await client.get("/internal/job-matcher/subscriptions")
            admin_response = await client.get(
                "/api/v1/public/job-matcher/subscriptions",
                headers={
                    "Authorization": f"Bearer {create_access_token(str(uuid.uuid4()), 'admin')}"
                },
            )
            user_response = await client.get(
                "/api/v1/public/job-matcher/subscriptions",
                headers={
                    "Authorization": f"Bearer {create_access_token(str(uuid.uuid4()), 'user')}"
                },
            )
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == str(subscription.id)
    assert payload["items"][0]["auth_id"] == str(auth_id)
    assert payload["items"][0]["category_ids"] == [str(category_id)]
    assert admin_response.status_code == 200
    assert admin_response.json() == payload
    assert user_response.status_code == 401


async def test_get_offers_for_admin_ui(db_session: AsyncSession) -> None:
    category_id = uuid.uuid4()
    offer = await JobOfferRepository().create(
        db_session,
        {
            "title": "Python Developer",
            "description": "Полный текст вакансии",
            "tags": ["python"],
            "location": "Удалённо",
            "source_chat_id": 123,
            "source_message_id": 456,
            "category_ids": [str(category_id)],
        },
    )

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY},
        ) as client:
            admin_response = await client.get(
                "/api/v1/public/job-matcher/offers",
                headers={
                    "Authorization": f"Bearer {create_access_token(str(uuid.uuid4()), 'admin')}"
                },
            )
            user_response = await client.get(
                "/api/v1/public/job-matcher/offers",
                headers={
                    "Authorization": f"Bearer {create_access_token(str(uuid.uuid4()), 'user')}"
                },
            )
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert admin_response.status_code == 200
    payload = admin_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == str(offer.id)
    assert payload["items"][0]["description"] == "Полный текст вакансии"
    assert payload["items"][0]["category_ids"] == [str(category_id)]
    assert user_response.status_code == 401
