"""A module contributes resources and behavior; the host owns infrastructure."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter

from src.base.configuration.schema import BaseModuleConfig
from src.base.configuration.service import BaseConfigService
from src.base.model import Base
from src.bus.interface import MessageConsumer, MessageProducer


@dataclass
class ModuleContext:
    producer: MessageProducer
    consumer: MessageConsumer
    safe_mode: bool
    services: dict[str, Any] = field(default_factory=dict)
    configs: dict[str, BaseModuleConfig] = field(default_factory=dict)


async def no_op(context: ModuleContext) -> None:
    pass


@dataclass(frozen=True)
class ModuleDefinition:
    name: str
    router: APIRouter
    models: tuple[type[Base], ...]
    configuration: BaseConfigService[Any, Any]
    install_config: Callable[[Any], None]
    clear_config: Callable[[], None]
    prepare: Callable[[ModuleContext], Awaitable[None]] = no_op
    start: Callable[[ModuleContext], Awaitable[None]] = no_op
    quiesce: Callable[[ModuleContext], Awaitable[None]] = no_op
    stop: Callable[[ModuleContext], Awaitable[None]] = no_op
