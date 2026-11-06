"""Fresh-process offline startup probe, executed by test_safe_mode.py."""

import asyncio
import importlib.abc
import sys

network_attempts = []


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        network_attempts.append(event)
        raise AssertionError(f"Network access in safe mode: {event}")


class DenyHeavyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {
            "torch",
            "sentence_transformers",
            "faster_whisper",
            "huggingface_hub",
            "langchain_google_genai",
            "langchain_openai",
            "langchain_mistralai",
        }:
            raise AssertionError(f"Heavy SDK imported in safe mode: {fullname}")
        return None


sys.addaudithook(deny_network)
sys.meta_path.insert(0, DenyHeavyImports())

import httpx  # noqa: E402
from sqlalchemy import text  # noqa: E402

from src.bus.in_memory.producer import InMemoryProducer  # noqa: E402
from src.core.config import settings  # noqa: E402
from src.core.database import create_async_session  # noqa: E402
from src.main import app  # noqa: E402


async def probe():
    assert settings.SAFE_MODE
    assert settings.DATABASE_URL.startswith("sqlite+aiosqlite:///")
    assert isinstance(app.state.container.producer, InMemoryProducer)
    for _ in range(2):
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://offline"
            ) as client,
        ):
            async with create_async_session() as session:
                assert (await session.execute(text("PRAGMA foreign_keys"))).scalar_one() == 1
            assert (await client.get("/health")).json() == {"status": "ok"}
            response = await client.post(
                "/api/v1/public/auth/login",
                json={
                    "identifier": settings.ADMIN_EMAIL,
                    "password": settings.ADMIN_PASSWORD,
                },
            )
            assert response.status_code == 200, response.text
            headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
            for path in ["/users/", "/memory/conversations/"]:
                assert (
                    await client.get("/api/v1/public" + path, headers=headers)
                ).status_code == 200
            for path in ["/telegram/accounts/", "/instagram/accounts/"]:
                response = await client.get("/api/v1/public" + path, headers=headers)
                assert response.status_code == 503, response.text
                assert "SAFE_MODE" in response.json()["detail"]
    assert not network_attempts, network_attempts
    print("Offline startup, restart, login, local APIs, integration guards: OK")


asyncio.run(probe())
