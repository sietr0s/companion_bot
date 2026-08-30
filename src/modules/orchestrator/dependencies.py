"""Orchestrator module dependency injection factories."""

from src.bus.interface import MessageConsumer, MessageProducer
from src.modules.orchestrator.service import OrchestratorService


async def get_orchestrator_service(
    message_consumer: MessageConsumer,
    message_producer: MessageProducer,
) -> OrchestratorService:
    """Get orchestrator service instance."""
    service = OrchestratorService(
        message_consumer=message_consumer,
        message_producer=message_producer,
    )
    service.register_all_handlers()
    return service
