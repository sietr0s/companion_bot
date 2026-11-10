"""Construct one batch accumulator per handler registration."""

from src.bus.interface import MessageProducer
from src.modules.batching.config import BatchingSettings
from src.modules.batching.service import BatchService


def build_batch_service(producer: MessageProducer, config: BatchingSettings) -> BatchService:
    return BatchService(producer, config=config)
