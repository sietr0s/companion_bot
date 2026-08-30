"""Orchestrator module bus event handlers.

Note: Orchestrator registers its handlers directly in the service
via register_all_handlers() method, so this file is minimal.
"""

from src.bus.interface import MessageConsumer
from src.modules.orchestrator.service import OrchestratorService


def register_handlers(consumer: MessageConsumer, service: OrchestratorService) -> None:
    """Register orchestrator event handlers.

    Orchestrator handlers are registered internally via service.register_all_handlers().
    This function is provided for API compatibility.
    """
    # Handlers are already registered in get_orchestrator_service dependency
    pass
