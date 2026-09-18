"""instagram_account, instagram_settings, instagram_chat_state.

Revision ID: 20260918_instagram_tables
Revises: 20260918_user_platform
Create Date: 2026-09-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260918_instagram_tables"
down_revision: str | Sequence[str] | None = "20260918_user_platform"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instagram_account",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("instagram_pk", sa.BigInteger(), nullable=True),
        sa.Column("session_file", sa.String(length=500), nullable=False),
        sa.Column("is_connected", sa.Boolean(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "instagram_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("use_whitelist", sa.Boolean(), nullable=False),
        sa.Column("whitelist_user_pks", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["instagram_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_instagram_settings_account_id", "instagram_settings", ["account_id"])
    op.create_table(
        "instagram_chat_state",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("last_item_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["instagram_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "thread_id", name="uq_instagram_chat_state_account_thread"),
    )
    op.create_index("ix_instagram_chat_state_account_id", "instagram_chat_state", ["account_id"])
    op.create_index("ix_instagram_chat_state_thread_id", "instagram_chat_state", ["thread_id"])


def downgrade() -> None:
    op.drop_table("instagram_chat_state")
    op.drop_table("instagram_settings")
    op.drop_table("instagram_account")
