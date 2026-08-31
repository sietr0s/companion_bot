"""Orchestrator bus registration."""

from src.bus.interface import MessageConsumer, MessageProducer
from src.modules.orchestrator.service import OrchestratorService


def register_handlers(consumer: MessageConsumer, producer: MessageProducer) -> OrchestratorService:
    service = OrchestratorService(consumer, producer)
    service.register_all_handlers()
    return service
