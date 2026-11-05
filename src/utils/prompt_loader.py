"""Read module-owned prompts without importing another module's implementation."""

from functools import lru_cache
from pathlib import Path

_MODULES = Path(__file__).resolve().parents[1] / "modules"


@lru_cache(maxsize=64)
def load_prompt(name: str, *, module: str = "llm") -> str:
    if not name.isidentifier() or not module.isidentifier():
        raise ValueError("Prompt and module names must be identifiers")
    return (_MODULES / module / "prompts" / f"{name}.md").read_text(encoding="utf-8").strip()


def render_prompt(name: str, *, module: str = "llm", **kwargs: object) -> str:
    return load_prompt(name, module=module).format(**kwargs)
