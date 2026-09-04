"""Persistence for behavior state."""

from __future__ import annotations

import random
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.behavior.life import roll_life, should_roll
from src.modules.behavior.models import BehaviorAccountState, BehaviorChatState


class BehaviorRepository:
    async def get_or_create_account(
        self,
        session: AsyncSession,
        account_id: UUID,
        now: datetime,
        rng: random.Random,
    ) -> BehaviorAccountState:
        result = await session.execute(
            select(BehaviorAccountState).where(BehaviorAccountState.account_id == account_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            life, until = roll_life(now, rng)
            row = BehaviorAccountState(
                account_id=account_id,
                activity=life.activity,
                mood=life.mood,
                activity_until=until,
                updated_at=now,
            )
            session.add(row)
            await session.flush()
            return row
        if should_roll(row.activity_until, now):
            life, until = roll_life(now, rng)
            row.activity = life.activity
            row.mood = life.mood
            row.activity_until = until
            row.updated_at = now
            await session.flush()
        return row

    async def get_or_create_chat(
        self,
        session: AsyncSession,
        account_id: UUID,
        chat_id: int,
    ) -> BehaviorChatState:
        result = await session.execute(
            select(BehaviorChatState).where(
                BehaviorChatState.account_id == account_id,
                BehaviorChatState.chat_id == chat_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = BehaviorChatState(
                account_id=account_id,
                chat_id=chat_id,
                consecutive_voice_out=0,
                last_delivery=None,
            )
            session.add(row)
            await session.flush()
        return row

    async def note_delivery(
        self,
        session: AsyncSession,
        account_id: UUID,
        chat_id: int,
        channel: str,
    ) -> None:
        row = await self.get_or_create_chat(session, account_id, chat_id)
        if channel == "voice":
            row.consecutive_voice_out = (row.consecutive_voice_out or 0) + 1
            row.last_delivery = "voice"
        else:
            row.consecutive_voice_out = 0
            row.last_delivery = "text"
        await session.flush()
