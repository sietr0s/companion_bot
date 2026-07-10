"""add_telegram_chat_state_table

Revision ID: 9f37893a21c4
Revises: 175242240000
Create Date: 2026-07-09 16:43:01.835226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f37893a21c4'
down_revision: Union[str, Sequence[str], None] = '175242240000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'telegram_chat_state',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('last_read_message_id', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ['account_id'],
            ['telegram_account.id'],
            ondelete='CASCADE'
        ),
        sa.UniqueConstraint('account_id', 'chat_id', name='uq_telegram_chat_state_account_chat'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создаём индексы
    op.create_index('ix_telegram_chat_state_account_id', 'telegram_chat_state', ['account_id'])
    op.create_index('ix_telegram_chat_state_chat_id', 'telegram_chat_state', ['chat_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индексы
    op.drop_index('ix_telegram_chat_state_chat_id', table_name='telegram_chat_state')
    op.drop_index('ix_telegram_chat_state_account_id', table_name='telegram_chat_state')
    
    # Удаляем таблицу
    op.drop_table('telegram_chat_state')
