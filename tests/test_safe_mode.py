"""Verify the offline composition in a fresh process with all socket I/O denied."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.core.config import settings
from src.core.exceptions import AppException


def test_offline_startup_without_network_or_heavy_sdks(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "tests.smoke_safe_mode"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            **os.environ,
            "SAFE_MODE": "true",
            "SAFE_MODE_DATABASE_PATH": str(tmp_path / "offline.db"),
            "DB_HOST": "unreachable.invalid",
            "MESSAGE_BUS": "kafka",
            "LLM_PROVIDER": "mistral",
            "STT_PROVIDER": "faster_whisper",
            "TTS_PROVIDER": "openai",
            "LANGSMITH_TRACING": "true",
            "CREATE_TABLES_ON_STARTUP": "false",
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Offline startup" in result.stdout


@pytest.mark.parametrize(
    "factory",
    [
        "src.modules.llm.dependencies:get_embedder",
        "src.modules.llm.dependencies:get_chat_provider",
        "src.modules.llm.dependencies:build_chat_provider",
        "src.modules.stt.dependencies:get_stt_provider",
        "src.modules.stt.dependencies:build_stt_provider",
        "src.modules.tts.dependencies:get_tts_provider",
    ],
)
def test_safe_mode_rejects_ai_even_when_provider_is_cached(monkeypatch, factory):
    from importlib import import_module

    monkeypatch.setattr(settings, "SAFE_MODE", True)
    module, name = factory.split(":")
    with pytest.raises(AppException, match="SAFE_MODE") as error:
        getattr(import_module(module), name)()
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_safe_database_initializes_locally_with_constraints(tmp_path, monkeypatch):
    from sqlalchemy import text

    from src.core.database import create_async_session, dispose_db, init_db

    monkeypatch.setattr(settings, "SAFE_MODE", True)
    monkeypatch.setattr(settings, "SAFE_MODE_DATABASE_PATH", str(tmp_path / "local.db"))
    monkeypatch.setattr(settings, "CREATE_TABLES_ON_STARTUP", False)
    await init_db()
    try:
        async with create_async_session() as session:
            assert (await session.execute(text("PRAGMA foreign_keys"))).scalar_one() == 1
            assert (
                await session.execute(text("SELECT count(*) FROM conversations"))
            ).scalar_one() == 0
    finally:
        await dispose_db()


def test_safe_mode_never_enables_langsmith(monkeypatch):
    from src.core.langsmith import configure_langsmith

    monkeypatch.setattr(settings, "SAFE_MODE", True)
    monkeypatch.setattr(settings, "LANGSMITH_TRACING", True)
    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "test-key-never-used")
    before = dict(os.environ)
    assert configure_langsmith() is False
    assert dict(os.environ) == before
