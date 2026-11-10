from pydantic import Field, model_validator

from src.base.configuration.schema import BaseModuleConfig


class MemoryConfiguration(BaseModuleConfig):
    SUMMARY_THRESHOLD: int = Field(default=50, ge=1)
    CLUSTER_MIN_MESSAGES: int = Field(default=20, ge=2)
    CLUSTER_HARD_CAP: int = Field(default=50, ge=2)
    CLUSTER_RETRIES: int = Field(default=3, ge=1)
    VECTOR_TOP_K: int = Field(default=10, ge=1)
    RETRIEVE_PRE_WINDOW: int = Field(default=8, ge=1)
    SNIPPET_MAX_MESSAGES: int = Field(default=12, ge=1)
    TOPIC_EMBED_MAX_CHARS: int = Field(default=400, ge=1)

    @model_validator(mode="after")
    def validate_window(self) -> "MemoryConfiguration":
        if self.CLUSTER_HARD_CAP < self.CLUSTER_MIN_MESSAGES:
            raise ValueError("CLUSTER_HARD_CAP must be >= CLUSTER_MIN_MESSAGES")
        return self
