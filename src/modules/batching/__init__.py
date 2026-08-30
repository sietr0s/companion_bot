"""Batching module for message batching."""

from src.modules.batching.dependencies import get_batching_service
from src.modules.batching.service import BatchService

__all__ = [
    "get_batching_service",
    "BatchService",
]
