"""Persistent on-disk cache for Hugging Face / sentence-transformers / torch weights."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from src.core.config import settings

logger = logging.getLogger(__name__)


def apply_model_cache() -> Path:
    root = Path(settings.MODEL_CACHE_DIR)
    if not root.is_absolute():
        root = Path.cwd() / root
    hf = root / "huggingface"
    st = root / "sentence-transformers"
    torch_dir = root / "torch"
    for path in (hf, st, torch_dir, hf / "hub"):
        path.mkdir(parents=True, exist_ok=True)

    os.environ["HF_HOME"] = str(hf)
    os.environ["HF_HUB_CACHE"] = str(hf / "hub")
    os.environ["TRANSFORMERS_CACHE"] = str(hf)
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(st)
    os.environ["TORCH_HOME"] = str(torch_dir)
    logger.info("Кэш моделей: %s", root)
    return root
