"""Explicit module registry; import only selected module entrypoints."""

from importlib import import_module

from src.core.application.module import ModuleDefinition

MODULE_NAMES = (
    "auth",
    "users",
    "llm",
    "telegram_clients",
    "instagram_clients",
    "stt",
    "tts",
    "memory",
    "behavior",
    "batching",
    "orchestrator",
)


def load_modules(names: tuple[str, ...] = MODULE_NAMES) -> tuple[ModuleDefinition, ...]:
    if len(set(names)) != len(names) or set(names) - set(MODULE_NAMES):
        raise ValueError("Unknown or duplicate application modules")
    return tuple(import_module(f"src.modules.{name}.main").get_module() for name in names)
