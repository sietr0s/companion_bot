"""add Telegram sender fields to job offers

Revision ID: 176347200000
Revises: 9f37893a21c4
Create Date: 2026-07-18 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "176347200000"
down_revision: str | None = "9f37893a21c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable Telegram author details to existing offers."""
    op.add_column(
        "job_offers",
        sa.Column("telegram_sender_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "job_offers",
        sa.Column("telegram_username", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "job_offers",
        sa.Column("telegram_first_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "job_offers",
        sa.Column("telegram_last_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Remove Telegram author details from offers."""
    op.drop_column("job_offers", "telegram_last_name")
    op.drop_column("job_offers", "telegram_first_name")
    op.drop_column("job_offers", "telegram_username")
    op.drop_column("job_offers", "telegram_sender_id")
