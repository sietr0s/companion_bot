"""Policy engine: criteria, filters, noise, softmax."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Protocol

from src.core.config import settings


@dataclass(frozen=True)
class LifeSnapshot:
    activity: str = "working"
    mood: str = "neutral"


@dataclass(frozen=True)
class ChatSnapshot:
    consecutive_voice_out: int = 0
    last_delivery: str | None = None


@dataclass
class DecisionContext:
    incoming_text: str = ""
    incoming_types: tuple[str, ...] = ()
    outgoing_text: str = ""
    life: LifeSnapshot = field(default_factory=LifeSnapshot)
    chat: ChatSnapshot = field(default_factory=ChatSnapshot)
    needs_reply: int = 1
    asked_voice: int = 0
    emotion: int = 0
    now: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class Criterion(Protocol):
    name: str

    def deltas(self, ctx: DecisionContext) -> Mapping[str, float]: ...


class ActionFilter(Protocol):
    name: str

    def blocked(self, ctx: DecisionContext) -> Mapping[str, str]: ...


@dataclass(frozen=True)
class Policy:
    name: str
    legal_actions: tuple[str, ...]
    base_weights: dict[str, float]
    criteria: tuple[Criterion, ...]
    filters: tuple[ActionFilter, ...]
    fallback: str


@dataclass(frozen=True)
class Decision:
    action: str
    scores: dict[str, float]
    blocked: dict[str, str]


def apply_noise(weights: dict[str, float], rng: random.Random) -> dict[str, float]:
    return {key: max(value * rng.uniform(0.95, 1.05), 0.0) for key, value in weights.items()}


def softmax_sample(
    weights: dict[str, float],
    rng: random.Random,
    temperature: float = 1.0,
    fallback: str = "text",
) -> str:
    temp = temperature if temperature > 0 else 1.0
    keys = list(weights)
    if not keys:
        return fallback
    scaled = [math.exp(weights[k] / temp) if weights[k] > 0 else 0.0 for k in keys]
    total = sum(scaled)
    if total <= 0:
        return fallback
    pick = rng.random() * total
    cumulative = 0.0
    for key, mass in zip(keys, scaled, strict=True):
        cumulative += mass
        if pick <= cumulative:
            return key
    return keys[-1]


def decide(
    policy: Policy,
    ctx: DecisionContext,
    rng: random.Random,
    temperature: float | None = None,
) -> Decision:
    weights = {action: float(policy.base_weights.get(action, 0.0)) for action in policy.legal_actions}
    for criterion in policy.criteria:
        for action, delta in criterion.deltas(ctx).items():
            if action in weights:
                weights[action] += delta
    blocked: dict[str, str] = {}
    for action_filter in policy.filters:
        for action, reason in action_filter.blocked(ctx).items():
            if action in weights:
                blocked[action] = reason
    for action in blocked:
        weights[action] = 0.0
    noisy = apply_noise(weights, rng)
    temp = settings.BEHAVIOR_SOFTMAX_TEMP if temperature is None else temperature
    action = softmax_sample(noisy, rng, temperature=temp, fallback=policy.fallback)
    return Decision(action=action, scores=noisy, blocked=blocked)
