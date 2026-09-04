from datetime import UTC, datetime, timedelta
import random

from src.modules.behavior.life import roll_life, should_roll


def test_should_roll_when_expired():
    now = datetime.now(UTC)
    assert should_roll(now - timedelta(seconds=1), now) is True
    assert should_roll(now + timedelta(hours=1), now) is False
    assert should_roll(None, now) is True


def test_roll_life_until_between_2_and_4_hours():
    now = datetime.now(UTC)
    life, until = roll_life(now, random.Random(0))
    assert life.activity in {"working", "resting", "running", "public"}
    delta = (until - now).total_seconds()
    assert 2 * 3600 <= delta <= 4 * 3600
