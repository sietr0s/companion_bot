"""Rename telegram_* chat keys to channel + account_id + chat_id.

Revision ID: 20260918_channel_neutral_ids
Revises: 20260918_instagram_tables
Create Date: 2026-09-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260918_channel_neutral_ids"
down_revision: str | Sequence[str] | None = "20260918_instagram_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("channel", sa.String(length=32), nullable=True),
    )
    op.execute("UPDATE conversations SET channel = 'telegram' WHERE channel IS NULL")
    op.alter_column("conversations", "channel", existing_type=sa.String(length=32), nullable=False)
    op.alter_column("conversations", "telegram_chat_id", new_column_name="chat_id")
    op.alter_column("conversations", "telegram_account_id", new_column_name="account_id")
    op.drop_constraint("uq_conversations_account_chat", "conversations", type_="unique")
    op.create_unique_constraint(
        "uq_conversations_channel_account_chat",
        "conversations",
        ["channel", "account_id", "chat_id"],
    )

    op.add_column("batches", sa.Column("channel", sa.String(length=32), nullable=True))
    op.execute("UPDATE batches SET channel = 'telegram' WHERE channel IS NULL")
    op.alter_column("batches", "channel", existing_type=sa.String(length=32), nullable=False)
    op.alter_column("batches", "telegram_chat_id", new_column_name="chat_id")
    op.alter_column("batches", "telegram_account_id", new_column_name="account_id")

    op.add_column(
        "behavior_chat_state",
        sa.Column("channel", sa.String(length=32), nullable=True),
    )
    op.execute("UPDATE behavior_chat_state SET channel = 'telegram' WHERE channel IS NULL")
    op.alter_column(
        "behavior_chat_state", "channel", existing_type=sa.String(length=32), nullable=False
    )
    op.drop_constraint("uq_behavior_chat_state_account_chat", "behavior_chat_state", type_="unique")
    op.create_unique_constraint(
        "uq_behavior_chat_state_channel_account_chat",
        "behavior_chat_state",
        ["channel", "account_id", "chat_id"],
    )
    op.drop_constraint(
        "behavior_account_state_account_id_fkey", "behavior_account_state", type_="foreignkey"
    )
    op.drop_constraint(
        "behavior_chat_state_account_id_fkey", "behavior_chat_state", type_="foreignkey"
    )


def downgrade() -> None:
    raise NotImplementedError("channel-neutral ids are not reversed")
