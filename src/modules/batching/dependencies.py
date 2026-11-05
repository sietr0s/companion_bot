"""Construct one batch accumulator per handler registration."""

from src.bus.interface import MessageProducer
from src.modules.batching.service import BatchService


def build_batch_service(producer: MessageProducer) -> BatchService:
    return BatchService(producer)
