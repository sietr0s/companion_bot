from typing import Literal

from pydantic import Field, field_validator, model_validator

from src.base.configuration.schema import BaseModuleConfig
from src.core.settings import EnvironmentSettings
from src.modules.llm.presets import SamplingPreset, parse_llm_presets


class LLMConfiguration(BaseModuleConfig):
    # Chat provider.
    LLM_PROVIDER: Literal["stub", "mistral", "google", "openrouter", "openai", "openai_compat"] = (
        "mistral"
    )

    # Mistral.
    MISTRAL_MODEL: str = "mistral-small-latest"

    # Google Gemini.
    GOOGLE_MODEL: str = ""

    # OpenAI-compatible (OpenRouter / OpenAI / custom).
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "openai/gpt-4o-mini"

    # Local sentence-transformers embeddings.

    # JSON object merged onto reply/rag/extract defaults. Blank keeps the defaults.
    LLM_PRESETS: str = ""

    @field_validator("LLM_PROVIDER", mode="before")
    @classmethod
    def normalize_provider(cls, value: object) -> str:
        default = cls.model_fields["LLM_PROVIDER"].default
        if value is None:
            return str(default)
        text = str(value).strip().lower()
        return text or str(default)

    @field_validator(
        "LLM_BASE_URL",
        mode="before",
    )
    @classmethod
    def strip_blank(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @model_validator(mode="after")
    def _validate_presets(self) -> "LLMConfiguration":
        parse_llm_presets(self.LLM_PRESETS)
        return self

    def presets(self) -> dict[str, SamplingPreset]:
        return parse_llm_presets(self.LLM_PRESETS)


class LLMBootstrapSettings(EnvironmentSettings):
    MISTRAL_API_KEY: str = Field(default="", repr=False)
    GOOGLE_API_KEY: str = Field(default="", repr=False)
    LLM_API_KEY: str = Field(default="", repr=False)
    EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-0.6B"

    @field_validator("MISTRAL_API_KEY", "GOOGLE_API_KEY", "LLM_API_KEY", mode="before")
    @classmethod
    def strip_credentials(cls, value: object) -> str:
        return "" if value is None else str(value).strip()


class LLMSettings(LLMConfiguration, LLMBootstrapSettings):
    """Public snapshot plus ENV-only provider credentials and structural model choice."""
