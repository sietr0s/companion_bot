"""Named chat sampling presets. Model and provider are not part of a preset."""

from __future__ import annotations

import json

from pydantic import BaseModel, Field


class SamplingPreset(BaseModel):
    temperature: float = Field(ge=0, le=2)
    top_p: float = Field(ge=0, le=1)
    max_tokens: int = Field(ge=1)


DEFAULT_PRESETS: dict[str, SamplingPreset] = {
    "reply": SamplingPreset(temperature=0.8, top_p=0.95, max_tokens=1024),
    "rag": SamplingPreset(temperature=0.1, top_p=1.0, max_tokens=512),
    "extract": SamplingPreset(temperature=0.0, top_p=1.0, max_tokens=1024),
}


def parse_llm_presets(raw: str) -> dict[str, SamplingPreset]:
    text = (raw or "").strip()
    if not text:
        return dict(DEFAULT_PRESETS)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM_PRESETS must be JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("LLM_PRESETS must be a JSON object")
    unknown = set(payload) - set(DEFAULT_PRESETS)
    if unknown:
        raise ValueError(f"unknown LLM preset: {sorted(unknown)}")
    resolved = dict(DEFAULT_PRESETS)
    for name, patch in payload.items():
        if not isinstance(patch, dict):
            raise ValueError(f"LLM preset {name} must be an object")
        extra = set(patch) - {"temperature", "top_p", "max_tokens"}
        if extra:
            raise ValueError(f"unknown field on LLM preset {name}: {sorted(extra)}")
        current = resolved[name].model_dump()
        current.update(patch)
        try:
            resolved[name] = SamplingPreset.model_validate(current)
        except Exception as exc:
            raise ValueError(f"invalid LLM preset {name}") from exc
    return resolved
