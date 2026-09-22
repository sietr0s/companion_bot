"""LLM module settings.

Chat provider selection (`mistral | openrouter | openai | openai_compat | stub`)
plus the embedding model name. The TTS module imports the OpenAI-compat fields
(LLM_API_KEY, LLM_BASE_URL) from here when using an OpenRouter-style endpoint.
"""

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

from src.modules.llm.presets import SamplingPreset, parse_llm_presets


class LLMSettings(BaseSettings):
    # Chat provider.
    LLM_PROVIDER: str = "mistral"

    # Mistral.
    MISTRAL_API_KEY: str = ""
    MISTRAL_MODEL: str = "mistral-small-latest"

    # Google Gemini.
    GOOGLE_API_KEY: str = ""
    GOOGLE_MODEL: str = ""

    # OpenAI-compatible (OpenRouter / OpenAI / custom).
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "openai/gpt-4o-mini"

    # Local sentence-transformers embeddings.
    EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-0.6B"

    # JSON object merged onto reply/rag/extract defaults. Blank keeps the defaults.
    LLM_PRESETS: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("LLM_PROVIDER", mode="before")
    @classmethod
    def normalize_provider(cls, value: object) -> str:
        default = cls.model_fields["LLM_PROVIDER"].default
        if value is None:
            return default
        text = str(value).strip().lower()
        return text or default

    @field_validator(
        "MISTRAL_API_KEY",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        mode="before",
    )
    @classmethod
    def strip_blank(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @model_validator(mode="after")
    def _validate_presets(self) -> "LLMSettings":
        parse_llm_presets(self.LLM_PRESETS)
        return self

    def presets(self) -> dict[str, SamplingPreset]:
        return parse_llm_presets(self.LLM_PRESETS)


llm_settings = LLMSettings()
