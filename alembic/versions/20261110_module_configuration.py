"""Add one configuration table for every remaining application module."""

import sqlalchemy as sa

from alembic import op

revision = "20261110_module_configuration"
down_revision = "20261110_batching_configuration"
branch_labels = None
depends_on = None

TABLES = (
    "auth_configuration",
    "users_configuration",
    "llm_configuration",
    "telegram_clients_configuration",
    "instagram_clients_configuration",
    "stt_configuration",
    "tts_configuration",
    "memory_configuration",
    "behavior_configuration",
    "orchestrator_configuration",
)


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        if not sa.inspect(bind).has_table(name):
            op.create_table(
                name,
                sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
                sa.Column("revision", sa.Integer(), nullable=False),
                sa.Column("overrides", sa.JSON(), nullable=False),
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=False,
                ),
                sa.Column("updated_by", sa.Uuid(), nullable=True),
                sa.CheckConstraint("id = 1"),
            )


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        if sa.inspect(bind).has_table(name):
            op.drop_table(name)
