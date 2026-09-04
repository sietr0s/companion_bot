"""behavior account and chat state

Revision ID: 20260904_behavior_state
Revises: 20260901_summary_cluster_checkpoint
Create Date: 2026-09-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260904_behavior_state"
down_revision: Union[str, Sequence[str], None] = "20260901_summary_cluster_checkpoint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "behavior_account_state",
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("activity", sa.String(length=32), nullable=False),
        sa.Column("mood", sa.String(length=32), nullable=False),
        sa.Column("activity_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["telegram_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("account_id"),
    )
    op.create_table(
        "behavior_chat_state",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("consecutive_voice_out", sa.Integer(), nullable=False),
        sa.Column("last_delivery", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["telegram_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "chat_id", name="uq_behavior_chat_state_account_chat"),
    )
    op.create_index("ix_behavior_chat_state_account_id", "behavior_chat_state", ["account_id"])
    op.create_index("ix_behavior_chat_state_chat_id", "behavior_chat_state", ["chat_id"])


def downgrade() -> None:
    op.drop_index("ix_behavior_chat_state_chat_id", table_name="behavior_chat_state")
    op.drop_index("ix_behavior_chat_state_account_id", table_name="behavior_chat_state")
    op.drop_table("behavior_chat_state")
    op.drop_table("behavior_account_state")
