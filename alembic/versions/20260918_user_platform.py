"""user: platform + platform_user_id, drop telegram_id.

Revision ID: 20260918_user_platform
Revises: 20260906_baseline
Create Date: 2026-09-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260918_user_platform"
down_revision: str | Sequence[str] | None = "20260906_baseline"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user", sa.Column("platform", sa.String(length=32), nullable=True))
    op.add_column("user", sa.Column("platform_user_id", sa.String(length=64), nullable=True))
    op.execute("UPDATE \"user\" SET platform = 'telegram', platform_user_id = CAST(telegram_id AS VARCHAR)")
    op.alter_column("user", "platform", existing_type=sa.String(length=32), nullable=False)
    op.alter_column("user", "platform_user_id", existing_type=sa.String(length=64), nullable=False)
    op.create_index("ix_user_platform", "user", ["platform"])
    op.create_index("ix_user_platform_user_id", "user", ["platform_user_id"])
    op.create_unique_constraint("uq_user_platform_user_id", "user", ["platform", "platform_user_id"])
    op.drop_constraint("user_telegram_id_key", "user", type_="unique")
    op.drop_index("ix_user_telegram_id", table_name="user")
    op.drop_column("user", "telegram_id")


def downgrade() -> None:
    op.add_column("user", sa.Column("telegram_id", sa.BigInteger(), nullable=True))
    op.execute("UPDATE \"user\" SET telegram_id = CAST(platform_user_id AS BIGINT) WHERE platform = 'telegram'")
    op.alter_column("user", "telegram_id", existing_type=sa.BigInteger(), nullable=False)
    op.create_index("ix_user_telegram_id", "user", ["telegram_id"], unique=True)
    op.drop_constraint("uq_user_platform_user_id", "user", type_="unique")
    op.drop_index("ix_user_platform_user_id", table_name="user")
    op.drop_index("ix_user_platform", table_name="user")
    op.drop_column("user", "platform_user_id")
    op.drop_column("user", "platform")
