"""Policy engine: criteria, filters, noise, softmax."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from src.modules.behavior.config import behavior_settings
from src.modules.behavior.report import format_pre_softmax_log

if TYPE_CHECKING:
    import random
    from collections.abc import Mapping
    from datetime import datetime

logger = logging.getLogger(__name__)


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
    channel: str = "telegram"
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
    probabilities: dict[str, float] = field(default_factory=dict)


def apply_noise(weights: dict[str, float], rng: random.Random) -> dict[str, float]:
    return {key: max(value * rng.uniform(0.95, 1.05), 0.0) for key, value in weights.items()}


def softmax_probabilities(
    weights: dict[str, float],
    temperature: float = 1.0,
) -> dict[str, float]:
    """Share of non-negative weights. Temperature 1 = linear; <1 sharpens."""
    temp = temperature if temperature > 0 else 1.0
    masses = {key: max(value, 0.0) ** (1.0 / temp) for key, value in weights.items()}
    total = sum(masses.values())
    if total <= 0:
        return dict.fromkeys(weights, 0.0)
    return {key: mass / total for key, mass in masses.items()}


def softmax_sample(
    weights: dict[str, float],
    rng: random.Random,
    temperature: float = 1.0,
    fallback: str = "text",
) -> str:
    probs = softmax_probabilities(weights, temperature)
    if sum(probs.values()) <= 0:
        return fallback
    pick = rng.random()
    cumulative = 0.0
    last = fallback
    for key, mass in probs.items():
        cumulative += mass
        last = key
        if pick <= cumulative:
            return key
    return last


def decide(
    policy: Policy,
    ctx: DecisionContext,
    rng: random.Random,
    temperature: float | None = None,
) -> Decision:
    weights = {
        action: float(policy.base_weights.get(action, 0.0)) for action in policy.legal_actions
    }
    base = dict(weights)
    contributions: list[tuple[str, dict[str, float]]] = []
    for criterion in policy.criteria:
        applied: dict[str, float] = {}
        for action, delta in criterion.deltas(ctx).items():
            if action in weights:
                weights[action] += delta
                applied[action] = delta
        if applied:
            contributions.append((criterion.name, applied))
    after_criteria = dict(weights)
    blocked: dict[str, str] = {}
    for action_filter in policy.filters:
        for action, reason in action_filter.blocked(ctx).items():
            if action in weights:
                blocked[action] = reason
    for action in blocked:
        weights[action] = 0.0
    noisy = apply_noise(weights, rng)
    logger.info(
        "\n%s",
        format_pre_softmax_log(
            policy=policy.name,
            base=base,
            contributions=contributions,
            after_criteria=after_criteria,
            blocked=blocked,
            before_softmax=noisy,
        ),
    )
    temp = behavior_settings.BEHAVIOR_SOFTMAX_TEMP if temperature is None else temperature
    probabilities = softmax_probabilities(noisy, temp)
    action = softmax_sample(noisy, rng, temperature=temp, fallback=policy.fallback)
    return Decision(action=action, scores=noisy, blocked=blocked, probabilities=probabilities)
