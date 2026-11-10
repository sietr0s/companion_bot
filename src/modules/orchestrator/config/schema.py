from pydantic import Field

from src.base.configuration.schema import BaseModuleConfig


class OrchestratorConfiguration(BaseModuleConfig):
    ORCHESTRATOR_CONTEXT_MESSAGES: int = Field(default=50, ge=1)
