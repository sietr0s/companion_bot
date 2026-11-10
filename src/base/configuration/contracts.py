"""Transport contracts for generated module configuration endpoints."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConfigPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    values: dict[str, Any]


class ConfigReset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    fields: list[str] = Field(min_length=1)


class ConfigRead(BaseModel):
    revision: int
    values: dict[str, Any]
    overrides: dict[str, Any]
    sources: dict[str, str]
    obsolete_keys: list[str]
    field_schema: dict[str, Any]
    apply_mode: Literal["restart"] = "restart"
    notice: str = "Saved settings apply on the next process restart"
