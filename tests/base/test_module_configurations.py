"""The same configuration contract applies to every independently stored module."""

from importlib import import_module

import pytest
from pydantic import ValidationError

from src.composition.modules import MODULE_NAMES, load_modules

URL_NAMES = {"telegram_clients": "telegram", "instagram_clients": "instagram"}
CHANGES = {
    "auth": {"ACCESS_TOKEN_EXPIRE_MINUTES": 42},
    "users": {},
    "llm": {"LLM_PROVIDER": "stub"},
    "telegram_clients": {"TG_DEVICE_MODEL": "test-device"},
    "instagram_clients": {"INSTAGRAM_POLL_INTERVAL_S": 30},
    "stt": {"WHISPER_MODEL": "tiny"},
    "tts": {"TTS_VOICE": "echo"},
    "memory": {"VECTOR_TOP_K": 7},
    "behavior": {"BEHAVIOR_INTAKE_TIMEOUT_S": 20},
    "batching": {"BATCH_MAX_SIZE": 4},
    "orchestrator": {"ORCHESTRATOR_CONTEXT_MESSAGES": 25},
}


@pytest.mark.parametrize("name", MODULE_NAMES)
async def test_each_module_api_persists_atomic_revision_and_rejects_secrets(
    name, api_client, admin_token, auth_token
):
    path = "/api/v1/public/" + URL_NAMES.get(name, name) + "/configuration"
    headers = {"Authorization": f"Bearer {admin_token}"}
    assert (await api_client.get(path)).status_code == 401
    assert (
        await api_client.get(path, headers={"Authorization": f"Bearer {auth_token}"})
    ).status_code == 403
    before = (await api_client.get(path, headers=headers)).json()
    assert before["revision"] == 0
    props = before["field_schema"].get("properties", {})
    assert not any(
        secret in props
        for secret in (
            "JWT_SECRET_KEY",
            "LLM_API_KEY",
            "ADMIN_PASSWORD",
            "API_HASH",
            "DATABASE_URL",
            "SAFE_MODE",
        )
    )
    rejected = await api_client.patch(
        path, headers=headers, json={"revision": 0, "values": {"JWT_SECRET_KEY": "private"}}
    )
    assert rejected.status_code == 422
    saved = await api_client.patch(
        path, headers=headers, json={"revision": 0, "values": CHANGES[name]}
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 1
    for key, value in CHANGES[name].items():
        assert saved.json()["values"][key] == value
        assert saved.json()["sources"][key] == "database"
    stale = await api_client.patch(
        path, headers=headers, json={"revision": 0, "values": CHANGES[name]}
    )
    assert stale.status_code == 409
    if CHANGES[name]:
        reset = await api_client.post(
            path + "/reset", headers=headers, json={"revision": 1, "fields": list(CHANGES[name])}
        )
        assert reset.status_code == 200
        assert reset.json()["overrides"] == {}


async def test_every_module_has_separate_singleton_table_and_revision(db_session):
    modules = load_modules()
    tables = [module.configuration.repository.model.__tablename__ for module in modules]
    assert len(set(tables)) == len(MODULE_NAMES)
    for module in modules:
        await module.configuration.load_snapshot(db_session)
    await modules[0].configuration.change(db_session, 0, CHANGES["auth"], None)
    for module in modules[1:]:
        assert (await module.configuration.read(db_session)).revision == 0


def test_runtime_binding_keeps_secrets_in_environment_and_freezes_snapshot(monkeypatch):
    from src.modules.llm.config import LLMConfiguration, binding

    monkeypatch.setenv("LLM_API_KEY", "  private-value  ")
    binding.install(LLMConfiguration(LLM_PROVIDER="stub"))
    try:
        assert binding.get().LLM_API_KEY == "private-value"
        assert "LLM_API_KEY" not in LLMConfiguration.model_fields
        with pytest.raises(ValidationError):
            binding.get().LLM_MODEL = "changed"
    finally:
        binding.clear()
    assert binding.get().LLM_API_KEY == "private-value"


def test_all_configuration_models_are_frozen():
    for name in MODULE_NAMES:
        config = import_module(f"src.modules.{name}.config")
        assert config.get_settings().model_config["frozen"] is True


@pytest.mark.parametrize(
    "name,values",
    [
        ("behavior", {"BEHAVIOR_TIMEZONE": "Not/A_Zone"}),
        ("instagram_clients", {"INSTAGRAM_POLL_INTERVAL_S": 0}),
        ("llm", {"LLM_PROVIDER": "unknown"}),
        ("memory", {"CLUSTER_MIN_MESSAGES": 30, "CLUSTER_HARD_CAP": 20}),
    ],
)
async def test_module_invariants_reject_invalid_atomic_updates(
    name, values, api_client, admin_token
):
    path = "/api/v1/public/" + URL_NAMES.get(name, name) + "/configuration"
    headers = {"Authorization": f"Bearer {admin_token}"}
    before = (await api_client.get(path, headers=headers)).json()
    response = await api_client.patch(path, headers=headers, json={"revision": 0, "values": values})
    assert response.status_code == 422
    assert (await api_client.get(path, headers=headers)).json() == before


@pytest.mark.parametrize(
    "module_name,variable,value,public_field",
    [
        ("telegram_clients", "TG_API_HASH", "private-hash", "TG_DEVICE_MODEL"),
        ("tts", "LLM_API_KEY", "private-key", "TTS_VOICE"),
    ],
)
def test_module_credentials_merge_only_into_runtime(
    module_name, variable, value, public_field, monkeypatch
):
    config = import_module(f"src.modules.{module_name}.config")
    monkeypatch.setenv(variable, value)
    snapshot = config.binding.runtime_schema().model_dump(include={public_field})
    schema = load_modules((module_name,))[0].configuration.schema
    config.binding.install(schema.model_validate(snapshot))
    try:
        runtime = config.get_settings()
        assert getattr(runtime, variable) == value
        assert variable not in schema.model_fields
        assert value not in repr(runtime)
    finally:
        config.binding.clear()
