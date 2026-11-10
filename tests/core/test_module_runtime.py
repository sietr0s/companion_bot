"""Exercise every module through its real host and saved configuration boundary."""

from dataclasses import replace
from importlib import import_module
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from src.composition.application import create_application
from src.composition.modules import MODULE_NAMES, load_modules
from src.core.application import host
from src.core.config import settings
from src.core.exceptions import AppException
from tests.conftest import TestSessionLocal


@pytest.fixture
def hosted_db(monkeypatch):
    initialize = AsyncMock()
    dispose = AsyncMock()
    monkeypatch.setattr(host, "init_db", initialize)
    monkeypatch.setattr(host, "dispose_db", dispose)
    monkeypatch.setattr(host, "create_async_session", TestSessionLocal)
    monkeypatch.setattr("src.core.database._async_session_factory", TestSessionLocal)
    for name in ("auth", "telegram_clients", "instagram_clients"):
        monkeypatch.setattr(f"src.modules.{name}.main.create_async_session", TestSessionLocal)
    return initialize, dispose


@pytest.mark.parametrize("name", MODULE_NAMES)
async def test_each_standalone_safe_host_loads_only_its_tables_and_exposes_configuration(
    name, hosted_db, monkeypatch, admin_token
):
    monkeypatch.setattr(settings, "SAFE_MODE", True)
    module = import_module(f"src.modules.{name}.main")
    config = import_module(f"src.modules.{name}.config")
    app = module.create_app()
    async with app.router.lifespan_context(app):
        assert app.state.modules == (name,)
        assert set(app.state.container.configs) == {name}
        snapshot = config.get_settings()
        public = getattr(app.state, name + "_config").model_dump()
        assert snapshot.model_dump(include=set(public)) == public
        expected_tables = {model.__table__ for model in module.get_module().models}
        assert set(hosted_db[0].call_args.kwargs["tables"]) == expected_tables
        urls = [url for url in app.openapi()["paths"] if url.endswith("/configuration")]
        assert len(urls) == 1
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/health")).json() == {"status": "ok"}
            response = await client.get(urls[0], headers={"Authorization": f"Bearer {admin_token}"})
            assert response.status_code == 200, response.text
            assert response.json()["apply_mode"] == "restart"
    assert config.binding._snapshot is None
    hosted_db[1].assert_awaited_once()


async def test_database_override_installed_before_prepare_and_unchanged_by_api_write(
    hosted_db, monkeypatch, db_session
):
    from src.modules.batching.config import binding, get_settings
    from src.modules.batching.config.service import BatchingConfigService

    monkeypatch.setattr(settings, "SAFE_MODE", True)
    monkeypatch.setenv("BATCH_MAX_SIZE", "8")
    service = BatchingConfigService()
    await service.change(db_session, 0, {"BATCH_MAX_SIZE": 3}, None)
    seen = []

    def wire(context):
        context.services.setdefault("derived_limit", get_settings().BATCH_MAX_SIZE)

    async def prepare(context):
        seen.append(context.services["derived_limit"])

    definition = replace(load_modules(("batching",))[0], prepare=prepare)
    app = host.create_host((definition,), wire_ports=wire)
    async with app.router.lifespan_context(app):
        assert seen == [3]
        await service.change(db_session, 1, {"BATCH_MAX_SIZE": 6}, None)
        assert get_settings().BATCH_MAX_SIZE == 3
    assert binding._snapshot is None
    async with app.router.lifespan_context(app):
        assert get_settings().BATCH_MAX_SIZE == 6
        assert seen == [3, 6]


@pytest.mark.parametrize("failure", ["database", "invalid_snapshot", "start"])
async def test_failed_startup_disposes_database_and_clears_snapshots(
    failure, hosted_db, monkeypatch, db_session
):
    from src.modules.batching.config import binding
    from src.modules.batching.config.model import BatchingConfigModel

    monkeypatch.setattr(settings, "SAFE_MODE", True)
    module = load_modules(("batching",))[0]
    if failure == "database":
        hosted_db[0].side_effect = RuntimeError("database unavailable")
    elif failure == "invalid_snapshot":
        await module.configuration.load_snapshot(db_session)
        await db_session.execute(
            update(BatchingConfigModel).values(overrides={"BATCH_MAX_SIZE": 0})
        )
        await db_session.commit()
    else:
        module = replace(module, start=AsyncMock(side_effect=RuntimeError("start failed")))
    app = host.create_host((module,))
    with pytest.raises((RuntimeError, ValueError)):
        async with app.router.lifespan_context(app):
            pytest.fail("invalid startup succeeded")
    hosted_db[1].assert_awaited_once()
    assert binding._snapshot is None


async def test_standalone_rejects_process_local_bus_before_opening_database(hosted_db, monkeypatch):
    monkeypatch.setattr(settings, "SAFE_MODE", False)
    monkeypatch.setattr(settings, "MESSAGE_BUS", "in_memory")
    app = create_application(("batching",), standalone=True)
    with pytest.raises(RuntimeError, match="MESSAGE_BUS=kafka"):
        async with app.router.lifespan_context(app):
            pytest.fail("standalone accepted an isolated queue")
    hosted_db[0].assert_not_awaited()


async def test_lifecycle_orders_registration_before_bus_and_drains_stop_events(
    hosted_db, monkeypatch
):
    monkeypatch.setattr(settings, "SAFE_MODE", True)
    received = []
    events = []

    async def prepare(context):
        events.append("prepare")

        @context.consumer.subscribe("test.shutdown")
        async def receive(payload):
            received.append(payload)

    async def start(context):
        events.append("start")
        await context.producer.publish("test.shutdown", {"stage": "start"})

    async def quiesce(context):
        events.append("quiesce")

    async def stop(context):
        events.append("stop")
        await context.producer.publish("test.shutdown", {"stage": "stop"})

    module = replace(
        load_modules(("batching",))[0], prepare=prepare, start=start, quiesce=quiesce, stop=stop
    )
    app = host.create_host((module,))
    async with app.router.lifespan_context(app):
        assert events == ["prepare", "start"]
    assert events == ["prepare", "start", "quiesce", "stop"]
    assert received == [{"stage": "start"}, {"stage": "stop"}]


async def test_normal_monolith_registers_all_modules_without_real_clients(hosted_db, monkeypatch):
    monkeypatch.setattr(settings, "SAFE_MODE", False)
    monkeypatch.setattr(settings, "MESSAGE_BUS", "in_memory")
    monkeypatch.setattr("src.modules.llm.main.warmup_heavy_models", AsyncMock())
    monkeypatch.setattr("src.modules.stt.main.warmup_stt", AsyncMock())
    tg_service = AsyncMock()
    tg_service.get_active_accounts.return_value = []
    ig_service = AsyncMock()
    monkeypatch.setattr(
        "src.modules.telegram_clients.main.get_telegram_client_service_factory",
        lambda **kw: tg_service,
    )
    monkeypatch.setattr(
        "src.modules.instagram_clients.main.build_instagram_account_service",
        lambda **kw: ig_service,
    )
    app = create_application()
    async with app.router.lifespan_context(app):
        assert set(app.state.container.configs) == set(MODULE_NAMES)
        subscribers = app.state.container.consumer.get_subscribers()
        assert len(subscribers) >= 10
        assert "batching" in app.state.container.services
        assert "media_downloader" in app.state.container.services
    tg_service.restore_tg_sessions.assert_awaited_once()
    ig_service.restore_sessions.assert_awaited_once()


@pytest.mark.parametrize(
    "name,port",
    [("memory", "memory_intelligence"), ("behavior", "chat_provider"), ("stt", "media_downloader")],
)
async def test_missing_required_port_fails_explicitly(name, port):
    from src.core.application.module import ModuleContext
    from tests.conftest import MockBus

    module = load_modules((name,))[0]
    with pytest.raises(RuntimeError, match="requires"):
        await module.prepare(ModuleContext(MockBus(), AsyncMock(), False))


def test_registry_rejects_unknown_or_duplicate_modules():
    for names in [("missing",), ("batching", "batching")]:
        with pytest.raises(ValueError):
            load_modules(names)


async def test_exception_handler_preserves_domain_status_and_reraises_unexpected():
    response = await host.app_exception_handler(
        None, AppException(status_code=409, detail="revision")
    )
    assert response.status_code == 409
    with pytest.raises(ValueError):
        await host.app_exception_handler(None, ValueError("unexpected"))


async def test_shutdown_flushes_batch_before_waiting_for_downstream_background(
    hosted_db, monkeypatch
):
    import asyncio

    from src.domain.chat import Message
    from src.modules.batching.schemas.events import AddMessageCommand
    from src.modules.batching.service import BatchService

    monkeypatch.setattr(settings, "SAFE_MODE", True)
    background = []
    completed = []

    async def prepare_batch(context):
        context.services["batching"] = BatchService(context.producer, max_size=10, idle_timeout=100)

    async def prepare_downstream(context):
        @context.consumer.subscribe("batching.event.batch.ready")
        async def receive(payload):
            async def work():
                await asyncio.sleep(0.01)
                completed.append(payload["batch"]["messages"][0]["text"])

            background.append(asyncio.create_task(work()))

    async def start_batch(context):
        await context.services["batching"].add_incoming_message(
            AddMessageCommand(
                channel="telegram", chat_id=1, account_id=uuid4(), message=Message(text="pending")
            )
        )

    async def stop_downstream(context):
        await asyncio.gather(*background)

    batching, orchestrator = load_modules(("batching", "orchestrator"))
    app = host.create_host(
        (
            replace(batching, prepare=prepare_batch, start=start_batch),
            replace(orchestrator, prepare=prepare_downstream, stop=stop_downstream),
        )
    )
    async with app.router.lifespan_context(app):
        pass
    assert completed == ["pending"]


@pytest.mark.parametrize(
    "name,port", [("memory", "memory_intelligence"), ("behavior", "chat_provider")]
)
async def test_injected_ai_port_does_not_load_local_llm_configuration(
    name, port, hosted_db, monkeypatch
):
    from src.bus import create_bus

    monkeypatch.setattr(settings, "SAFE_MODE", False)
    monkeypatch.setattr(settings, "MESSAGE_BUS", "kafka")
    groups = []

    def local_bus(*, group_id):
        groups.append(group_id)
        return create_bus("in_memory")

    monkeypatch.setattr(host, "create_bus", local_bus)
    adapter = AsyncMock()
    app = create_application((name,), standalone=True, ports={port: adapter})
    async with app.router.lifespan_context(app):
        assert set(app.state.container.configs) == {name}
        assert app.state.container.services[port] is adapter
    assert groups == [settings.KAFKA_GROUP_ID + "." + name]


async def test_shutdown_failure_still_closes_transports_and_database(hosted_db, monkeypatch):
    monkeypatch.setattr(settings, "SAFE_MODE", True)
    module = replace(
        load_modules(("batching",))[0],
        quiesce=AsyncMock(side_effect=RuntimeError("quiesce failed")),
    )
    app = host.create_host((module,))
    context = app.state.container
    producer_stop = AsyncMock(wraps=context.producer.stop)
    consumer_stop = AsyncMock(wraps=context.consumer.stop)
    monkeypatch.setattr(context.producer, "stop", producer_stop)
    monkeypatch.setattr(context.consumer, "stop", consumer_stop)
    with pytest.raises(RuntimeError, match="quiesce failed"):
        async with app.router.lifespan_context(app):
            pass
    producer_stop.assert_awaited_once()
    consumer_stop.assert_awaited_once()
    hosted_db[1].assert_awaited_once()


def test_host_rejects_empty_module_selection():
    with pytest.raises(ValueError, match="At least one"):
        host.create_host(())
