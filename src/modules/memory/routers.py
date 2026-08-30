"""Memory module HTTP routers (optional, for admin API)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session
from src.modules.memory.repository import MemoryRepository
from src.modules.memory.schemas_api import (
    ConversationListResponse,
    ConversationResponse,
)

router = APIRouter(prefix="/memory", tags=["memory"])


async def get_repo(session: AsyncSession = Depends(get_async_session)) -> MemoryRepository:
    """Get memory repository."""
    return MemoryRepository(session=session)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    repo: MemoryRepository = Depends(get_repo),
) -> ConversationResponse:
    """Get conversation by ID."""
    conversation = await repo.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return ConversationResponse.model_validate(conversation)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    repo: MemoryRepository = Depends(get_repo),
) -> ConversationListResponse:
    """List all conversations (simplified)."""
    # In real app, would implement proper listing with pagination
    return ConversationListResponse(conversations=[], total=0)
