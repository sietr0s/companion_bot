"""Compatibility entry point; admin bootstrap is owned by auth."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.bus import get_producer
from src.bus.interface import MessageProducer
from src.modules.auth.seed import seed_admin as _seed_admin


async def seed_admin(session: AsyncSession, producer: MessageProducer | None = None) -> None:
    await _seed_admin(session, producer or get_producer())
