"""Batching module dependencies."""

from fastapi import Depends

from src.bus import get_producer
from src.modules.batching.repository import BatchMessageRepository, BatchRepository
from src.modules.batching.service import BatchMessageService, BatchService


def get_batch_repository() -> BatchRepository:
    return BatchRepository()


def get_batch_message_repository() -> BatchMessageRepository:
    return BatchMessageRepository()


def get_batching_service(
    repository: BatchRepository = Depends(get_batch_repository),
    message_repository: BatchMessageRepository = Depends(get_batch_message_repository),
) -> BatchService:
    return BatchService(
        repository=repository,
        message_bus=get_producer(),
        message_repository=message_repository,
    )


def get_batch_message_service(
    repository: BatchMessageRepository = Depends(get_batch_message_repository),
) -> BatchMessageService:
    return BatchMessageService(repository=repository)
