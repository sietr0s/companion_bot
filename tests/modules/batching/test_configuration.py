"""The generated API persists validated, revisioned overrides without mutating runtime."""

from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ConflictError
from src.domain.chat import Message
from src.modules.batching.config import BatchingSettings
from src.modules.batching.config.model import BatchingConfigModel
from src.modules.batching.config.service import BatchingConfigService
from src.modules.batching.schemas.events import AddMessageCommand
from src.modules.batching.service import BatchService

PATH = "/api/v1/public/batching/configuration"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,payload",
    [
        ("GET", None),
        ("PATCH", {"revision": 0, "values": {}}),
        ("POST", {"revision": 0, "fields": ["BATCH_MAX_SIZE"]}),
    ],
)
async def test_all_configuration_endpoints_require_admin(api_client, auth_token, method, payload):
    path = PATH + ("/reset" if method == "POST" else "")
    assert (await api_client.request(method, path, json=payload)).status_code == 401
    assert (
        await api_client.request(
            method, path, json=payload, headers={"Authorization": f"Bearer {auth_token}"}
        )
    ).status_code == 403


@pytest.mark.asyncio
async def test_api_precedence_update_reset_and_revision(api_client, admin_token, monkeypatch):
    monkeypatch.setenv("BATCH_MAX_SIZE", "7")
    headers = {"Authorization": f"Bearer {admin_token}"}
    initial = (await api_client.get(PATH, headers=headers)).json()
    assert initial["values"]["BATCH_MAX_SIZE"] == 7
    assert initial["sources"]["BATCH_MAX_SIZE"] == "environment"
    assert "JWT_SECRET_KEY" not in initial["field_schema"]["properties"]
    changed = await api_client.patch(
        PATH,
        headers=headers,
        json={"revision": 0, "values": {"BATCH_MAX_SIZE": 3, "BATCH_IDLE_SECONDS": 0.5}},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["revision"] == 1
    assert changed.json()["sources"]["BATCH_MAX_SIZE"] == "database"
    assert changed.json()["apply_mode"] == "restart"
    stale = await api_client.patch(
        PATH, headers=headers, json={"revision": 0, "values": {"BATCH_MAX_SIZE": 99}}
    )
    assert stale.status_code == 409
    saved = (await api_client.get(PATH, headers=headers)).json()
    assert saved["values"]["BATCH_MAX_SIZE"] == 3
    reset = await api_client.post(
        PATH + "/reset", headers=headers, json={"revision": 1, "fields": ["BATCH_MAX_SIZE"]}
    )
    assert reset.status_code == 200
    assert reset.json()["values"]["BATCH_MAX_SIZE"] == 7
    assert reset.json()["values"]["BATCH_IDLE_SECONDS"] == 0.5
    assert reset.json()["revision"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "values",
    [
        {"BATCH_MAX_SIZE": 0, "BATCH_IDLE_SECONDS": 5},
        {"BATCH_IDLE_SECONDS": -1},
        {"BATCH_MAX_SIZE": None},
        {"JWT_SECRET_KEY": "hidden"},
    ],
)
async def test_invalid_patch_leaves_all_fields_and_revision_unchanged(
    api_client, admin_token, values
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    before = (await api_client.get(PATH, headers=headers)).json()
    response = await api_client.patch(
        PATH, headers=headers, json={"revision": before["revision"], "values": values}
    )
    assert response.status_code == 422, response.text
    assert (await api_client.get(PATH, headers=headers)).json() == before


@pytest.mark.asyncio
async def test_new_snapshot_observes_database_but_running_service_keeps_old_values(
    db_session, message_bus, monkeypatch
):
    monkeypatch.setenv("BATCH_MAX_SIZE", "2")
    service = BatchingConfigService()
    old = await service.load_snapshot(db_session)
    running = BatchService(message_bus, config=old)
    await service.change(db_session, 0, {"BATCH_MAX_SIZE": 1}, uuid4())
    assert old.BATCH_MAX_SIZE == 2
    reloaded = await service.load_snapshot(db_session)
    restarted = BatchService(message_bus, config=reloaded)
    command = AddMessageCommand(
        channel="telegram", chat_id=1, account_id=uuid4(), message=Message(text="hello")
    )
    assert await running.add_incoming_message(command) is None
    old_batch = await running.add_incoming_message(command)
    assert len(old_batch.batch.messages) == 2
    new_batch = await restarted.add_incoming_message(command)
    assert len(new_batch.batch.messages) == 1
    with pytest.raises(ValidationError):
        old.BATCH_MAX_SIZE = 10


@pytest.mark.asyncio
async def test_repository_compare_and_swap_and_singleton_constraint(db_session):
    service = BatchingConfigService()
    await service.load_snapshot(db_session)
    await service.repository.replace(db_session, 0, {"BATCH_MAX_SIZE": 3}, uuid4())
    await db_session.commit()
    with pytest.raises(ConflictError):
        await service.repository.replace(db_session, 0, {}, uuid4())
    await db_session.rollback()
    db_session.add(BatchingConfigModel(id=2, overrides={}, revision=0))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_obsolete_keys_are_retained_and_invalid_known_values_block_startup(db_session):
    service = BatchingConfigService()
    await service.load_snapshot(db_session)
    await db_session.execute(
        update(BatchingConfigModel).values(overrides={"RETIRED": "keep", "BATCH_MAX_SIZE": 4})
    )
    await db_session.commit()
    result = await service.read(db_session)
    assert result.obsolete_keys == ["RETIRED"]
    await service.change(db_session, 0, {"BATCH_MAX_SIZE": 5}, uuid4())
    row = await service.repository.read(db_session)
    assert row.overrides["RETIRED"] == "keep"
    await db_session.execute(update(BatchingConfigModel).values(overrides={"BATCH_MAX_SIZE": 0}))
    await db_session.commit()
    with pytest.raises(ValidationError):
        await service.load_snapshot(db_session)


def test_no_database_data_is_written_into_env_files(monkeypatch):
    monkeypatch.setenv("BATCH_MAX_SIZE", "6")
    assert BatchingConfigService().resolve({"BATCH_MAX_SIZE": 3}).BATCH_MAX_SIZE == 3
    assert BatchingSettings().BATCH_MAX_SIZE == 6


@pytest.mark.asyncio
async def test_failed_commit_rolls_back_override_and_revision(db_session, monkeypatch):
    from unittest.mock import AsyncMock

    service = BatchingConfigService()
    await service.load_snapshot(db_session)
    with monkeypatch.context() as patch:
        patch.setattr(db_session, "commit", AsyncMock(side_effect=RuntimeError("storage failed")))
        with pytest.raises(RuntimeError, match="storage failed"):
            await service.change(db_session, 0, {"BATCH_MAX_SIZE": 9}, uuid4())
    row = await service.repository.read(db_session)
    assert row.revision == 0
    assert row.overrides == {}


@pytest.mark.asyncio
async def test_lifespan_uses_persisted_values_only_after_restart(tmp_path, monkeypatch):
    from src.core.config import settings
    from src.core.database import create_async_session
    from src.main import create_app

    monkeypatch.setattr(settings, "SAFE_MODE", True)
    monkeypatch.setattr(settings, "SAFE_MODE_DATABASE_PATH", str(tmp_path / "restart.db"))
    monkeypatch.setenv("BATCH_MAX_SIZE", "8")
    app = create_app()
    async with app.router.lifespan_context(app):
        async with create_async_session() as session:
            await BatchingConfigService().change(session, 0, {"BATCH_MAX_SIZE": 3}, uuid4())
        assert app.state.batching_config.BATCH_MAX_SIZE == 8
    restarted = create_app()
    async with restarted.router.lifespan_context(restarted):
        assert restarted.state.batching_config.BATCH_MAX_SIZE == 3
        async with create_async_session() as session:
            await session.execute(
                update(BatchingConfigModel).values(overrides={"BATCH_MAX_SIZE": 0})
            )
            await session.commit()
    broken = create_app()
    with pytest.raises(ValidationError):
        async with broken.router.lifespan_context(broken):
            pytest.fail("Invalid persisted configuration must prevent startup")
