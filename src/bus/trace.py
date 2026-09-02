"""Compact bus publish/receive logs."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("src.bus")

_SKIP_KEYS = frozenset({"embedding", "embeddings", "qr_url", "password"})
_MAX_LEN = 300


def payload_preview(payload: Any, max_len: int = _MAX_LEN) -> str:
    if isinstance(payload, dict):
        slim = {k: v for k, v in payload.items() if k not in _SKIP_KEYS}
        text = str(slim)
    else:
        text = str(payload)
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def log_published(topic: str, payload: Any) -> None:
    logger.info("опубликовано topic=%s payload=%s", topic, payload_preview(payload))


def log_received(topic: str, handler_name: str, payload: Any) -> None:
    logger.info(
        "получено topic=%s handler=%s payload=%s",
        topic,
        handler_name,
        payload_preview(payload),
    )
