"""Change Subscription.categories to category_ids (UUID array)

Revision ID: 175242240000
Revises: abc123telegram_settings
Create Date: 2026-07-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '175242240000'
down_revision: str | None = 'abc123telegram_settings'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Переименовываем column categories -> category_ids
    # В SQLite нет прямого ALTER COLUMN, поэтому используем batch mode
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        # SQLite не поддерживает переименование JSON колонки с изменением типа
        # Поэтому просто меняем имя (тип остаётся JSON)
        batch_op.alter_column('categories', new_column_name='category_ids')


def downgrade() -> None:
    # Возвращаем имя обратно
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.alter_column('category_ids', new_column_name='categories')
