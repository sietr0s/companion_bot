"""Initial schema from current models.

Revision ID: 20260918_baseline
Revises:
Create Date: 2026-09-18
"""

from collections.abc import Sequence

from alembic import op

from src.base.model import Base
from src.modules.auth.models import Auth  # noqa: F401
from src.modules.behavior.models import BehaviorAccountState, BehaviorChatState  # noqa: F401
from src.modules.instagram_clients.models import (  # noqa: F401
    InstagramAccount,
    InstagramChatState,
    InstagramSettings,
)
from src.modules.memory.models import (  # noqa: F401
    Conversation,
    Message,
    MessageBatch,
    SummaryState,
    VectorRecord,
)
from src.modules.telegram_clients.models import (  # noqa: F401
    TelegramAccount,
    TelegramChatState,
    TelegramSettings,
)
from src.modules.users.models import User  # noqa: F401

revision: str = "20260918_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind)
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_vector_records_kind_conversation
            ON vector_records (kind, conversation_id)
            """
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_vector_records_embedding_hnsw
            ON vector_records USING hnsw (embedding vector_cosine_ops)
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_vector_records_embedding_hnsw")
        op.execute("DROP INDEX IF EXISTS ix_vector_records_kind_conversation")
    Base.metadata.drop_all(bind=bind)
