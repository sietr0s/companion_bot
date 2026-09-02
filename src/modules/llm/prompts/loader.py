"""Load LLM prompts from markdown files."""

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def render_prompt(name: str, **kwargs: object) -> str:
    return load_prompt(name).format(**kwargs)
