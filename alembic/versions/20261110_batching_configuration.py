"""Add the per-module batching configuration singleton."""

from alembic import op
from src.modules.batching.config.model import BatchingConfigModel

revision = "20261110_batching_configuration"
down_revision = "20260918_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The historical baseline registers current metadata on fresh installs.
    BatchingConfigModel.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    BatchingConfigModel.__table__.drop(op.get_bind(), checkfirst=True)
