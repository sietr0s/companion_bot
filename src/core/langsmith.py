"""Enable LangSmith tracing for LangChain LLM calls."""

from __future__ import annotations

import logging
import os

from src.core.config import settings

logger = logging.getLogger(__name__)


def configure_langsmith() -> bool:
    key = (settings.LANGSMITH_API_KEY or "").strip()
    tracing = bool(settings.LANGSMITH_TRACING) or bool(key)
    if not tracing:
        logger.info("LangSmith tracing выключен")
        return False
    if not key:
        logger.warning("LANGSMITH_TRACING=true, но LANGSMITH_API_KEY пустой")
        return False

    project = (settings.LANGSMITH_PROJECT or "companion_bot").strip()
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_API_KEY"] = key
    os.environ["LANGCHAIN_API_KEY"] = key
    os.environ["LANGSMITH_PROJECT"] = project
    os.environ["LANGCHAIN_PROJECT"] = project
    endpoint = (settings.LANGSMITH_ENDPOINT or "").strip()
    if endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = endpoint
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint
    logger.info("LangSmith tracing включён, project=%s", project)
    return True
