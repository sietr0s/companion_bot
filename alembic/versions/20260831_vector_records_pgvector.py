"""Enable pgvector and convert vector_records.embedding to vector(1024).

Revision ID: 20260831_vector_records_pgvector
Revises: 176347200000
Create Date: 2026-08-31 00:00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260831_vector_records_pgvector"
down_revision: str | None = "176347200000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # Ensure table exists (e.g. fresh envs without prior create_all).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vector_records (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            conversation_id UUID NOT NULL,
            text TEXT NOT NULL,
            embedding vector(1024),
            extra_data JSON
        )
        """
    )
    # Convert leftover JSON embeddings in place; skip if already vector(1024).
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'vector_records'
                  AND column_name = 'embedding'
                  AND udt_name IS DISTINCT FROM 'vector'
            ) THEN
                ALTER TABLE vector_records
                    ALTER COLUMN embedding TYPE vector(1024)
                    USING embedding::text::vector;
            END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE vector_records ALTER COLUMN embedding TYPE JSON USING NULL"
    )
