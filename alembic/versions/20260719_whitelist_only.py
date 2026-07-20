"""Reduce Telegram settings to whitelist-only permissions."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260719_whitelist_only"
down_revision: Union[str, None] = "abc123telegram_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "telegram_settings",
        sa.Column("use_whitelist", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.drop_column("telegram_settings", "read_groups")
    op.drop_column("telegram_settings", "read_personal")
    op.drop_column("telegram_settings", "read_channels")


def downgrade() -> None:
    op.add_column("telegram_settings", sa.Column("read_groups", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("telegram_settings", sa.Column("read_personal", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("telegram_settings", sa.Column("read_channels", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.drop_column("telegram_settings", "use_whitelist")
