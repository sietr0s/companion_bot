"""LLM module for text generation and summarization."""

from src.modules.llm.dependencies import get_llm_service
from src.modules.llm.service import LLMService

__all__ = [
    "LLMService",
    "get_llm_service",
]
