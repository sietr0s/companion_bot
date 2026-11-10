"""Process-lifecycle binding for immutable module snapshots."""

from typing import Generic, TypeVar

from src.base.configuration.schema import BaseModuleConfig
from src.core.settings import EnvironmentSettings

Public = TypeVar("Public", bound=BaseModuleConfig)
Runtime = TypeVar("Runtime", bound=EnvironmentSettings)


class ConfigBinding(Generic[Public, Runtime]):
    def __init__(self, runtime_schema: type[Runtime]):
        self.runtime_schema = runtime_schema
        self._snapshot: Runtime | None = None

    def get(self) -> Runtime:
        return self._snapshot if self._snapshot is not None else self.runtime_schema()

    def install(self, snapshot: Public) -> None:
        self._snapshot = self.runtime_schema.model_validate(snapshot.model_dump())

    def clear(self) -> None:
        self._snapshot = None
