"""Lazy activity/mood rotation."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from src.modules.behavior.engine import LifeSnapshot

ACTIVITIES = ("working", "resting", "running", "public")
MOODS = ("good", "neutral", "bad")


def should_roll(activity_until: datetime | None, now: datetime) -> bool:
    if activity_until is None:
        return True
    until = activity_until if activity_until.tzinfo else activity_until.replace(tzinfo=UTC)
    return until <= now


def roll_life(now: datetime, rng: random.Random) -> tuple[LifeSnapshot, datetime]:
    life = LifeSnapshot(rng.choice(list(ACTIVITIES)), rng.choice(list(MOODS)))
    until = now + timedelta(hours=rng.uniform(2.0, 4.0))
    return life, until
