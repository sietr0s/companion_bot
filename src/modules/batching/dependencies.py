"""Batching module dependencies."""

from functools import partial

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.bus.interface import MessageConsumer, MessageProducer
from src.core.database import get_session
from src.modules.batching.handlers import register_handlers
from src.modules.batching.repository import BatchRepository
from src.modules.batching.service import BatchService


def get_batching_repository(
    session: AsyncSession = Depends(get_session),
) -> BatchRepository:
    """Get batching repository."""
    return BatchRepository(session=session)


def get_batching_service(
    repository: BatchRepository = Depends(get_batching_repository),
    message_bus: MessageProducer = Depends(MessageProducer),  # type: ignore[arg-type]
) -> BatchService:
    """Get batching service."""
    return BatchService(repository=repository, message_bus=message_bus)


def get_batching_consumer(
    service: BatchService = Depends(get_batching_service),
) -> None:
    """Register batching handlers with the message consumer."""
    # This is called during app startup to register handlers
    pass


def register_batching_handlers_factory(
    consumer: MessageConsumer,
) -> callable:
    """Factory to register batching handlers."""
    return partial(register_handlers, consumer=consumer)
