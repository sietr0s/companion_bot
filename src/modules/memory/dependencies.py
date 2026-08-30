"""Memory module dependency injection factories."""


from sqlalchemy.ext.asyncio import AsyncSession

from src.bus.interface import MessageProducer
from src.modules.memory.repository import MemoryRepository
from src.modules.memory.service import MemoryService


async def get_memory_repository(session: AsyncSession) -> MemoryRepository:
    """Get memory repository instance."""
    return MemoryRepository(session=session)


async def get_memory_service(
    repository: MemoryRepository,
    message_bus: MessageProducer,
) -> MemoryService:
    """Get memory service instance."""
    return MemoryService(
        repository=repository,
        message_bus=message_bus,
    )
