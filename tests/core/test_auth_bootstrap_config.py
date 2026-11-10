"""Infrastructure and unrelated modules do not require Auth seed credentials."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.config import Settings
from src.modules.auth.config import AuthBootstrapSettings


def test_core_settings_do_not_require_or_expose_admin_credentials(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    config = Settings(_env_file=None, JWT_SECRET_KEY="test-only-key")
    assert "ADMIN_EMAIL" not in Settings.model_fields
    assert "ADMIN_PASSWORD" not in config.model_dump()


def test_auth_bootstrap_requires_credentials_only_when_constructed(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    with pytest.raises(ValidationError) as error:
        AuthBootstrapSettings(_env_file=None)
    assert {e["loc"][0] for e in error.value.errors()} == {"ADMIN_EMAIL", "ADMIN_PASSWORD"}


def test_bootstrap_password_is_masked():
    settings = AuthBootstrapSettings(
        _env_file=None, ADMIN_EMAIL="admin@example.com", ADMIN_PASSWORD="bootstrap-test-password"
    )
    assert "bootstrap-test-password" not in repr(settings)
    assert "bootstrap-test-password" not in settings.model_dump_json()
    assert settings.ADMIN_PASSWORD.get_secret_value() == "bootstrap-test-password"


def test_batching_import_and_construction_without_admin_credentials(tmp_path):
    environment = dict(
        os.environ,
        PYTHONPATH=str(Path(__file__).resolve().parents[2]),
        JWT_SECRET_KEY="test-key-with-more-than-32-characters",
        PYTHONDONTWRITEBYTECODE="1",
    )
    environment.pop("ADMIN_EMAIL", None)
    environment.pop("ADMIN_PASSWORD", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from src.bus import create_bus
from src.core.database import create_async_session
from src.modules.batching.config import BatchingSettings
from src.modules.batching.dependencies import build_batch_service
producer, consumer = create_bus('in_memory')
build_batch_service(producer, BatchingSettings())
assert not any(name.startswith('src.modules.auth') for name in sys.modules)
print('Batching needs no Auth bootstrap credentials or imports')
""",
        ],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "needs no Auth" in result.stdout


@pytest.mark.parametrize(
    "module_name",
    [
        "users",
        "llm",
        "telegram_clients",
        "instagram_clients",
        "stt",
        "tts",
        "memory",
        "behavior",
        "batching",
        "orchestrator",
    ],
)
def test_every_other_module_starts_offline_without_auth_imports_or_credentials(
    module_name, tmp_path
):
    environment = dict(
        os.environ,
        PYTHONPATH=str(Path(__file__).resolve().parents[2]),
        SAFE_MODE="true",
        SAFE_MODE_DATABASE_PATH=str(tmp_path / "module.db"),
        JWT_SECRET_KEY="test-key-with-more-than-32-characters",
        PYTHONDONTWRITEBYTECODE="1",
        SELECTED_MODULE=module_name,
    )
    environment.pop("ADMIN_EMAIL", None)
    environment.pop("ADMIN_PASSWORD", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import asyncio
import os
import sys

def deny_network(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
        raise AssertionError(f'Network access: {event}')
sys.addaudithook(deny_network)
from src.composition.application import create_service_app
app = create_service_app(os.environ['SELECTED_MODULE'])
async def run():
    async with app.router.lifespan_context(app):
        assert app.state.modules == (os.environ['SELECTED_MODULE'],)
        assert not any(name.startswith('src.modules.auth') for name in sys.modules)
        assert not any(name.split('.')[0] in {'torch', 'sentence_transformers', 'faster_whisper', 'langchain_openai'} for name in sys.modules)
asyncio.run(run())
print('isolated offline startup OK')
""",
        ],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "isolated offline startup OK" in result.stdout
