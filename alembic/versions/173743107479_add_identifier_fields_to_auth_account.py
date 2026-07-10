"""add_identifier_fields_to_auth_account

Revision ID: 173743107479
Revises:
Create Date: 2026-07-01 15:45:56.395172

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '173743107479'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: добавить поля identifier и identifier_type вместо email."""
    # Добавляем новые поля
    op.add_column("auth_account", sa.Column("identifier", sa.String(255), nullable=True))
    op.add_column("auth_account", sa.Column("identifier_type", sa.String(10), nullable=True))
    
    # Конвертируем существующие данные (если есть)
    # Предполагаем, что старые записи имеют email, который станет identifier
    op.execute("""
        UPDATE auth_account 
        SET identifier = email, 
            identifier_type = 'email'
        WHERE email IS NOT NULL
    """)
    
    # Делаем поля NOT NULL (для новых записей должны быть значения)
    op.alter_column("auth_account", "identifier", nullable=False)
    op.alter_column("auth_account", "identifier_type", nullable=False)
    
    # Создаем уникальный индекс на identifier
    op.create_unique_constraint("auth_account_identifier_key", "auth_account", ["identifier"])
    op.create_index("ix_auth_account_identifier", "auth_account", ["identifier"])
    
    # Удаляем старое поле email
    op.drop_index("ix_auth_account_email", "auth_account", if_exists=True)
    op.drop_constraint("auth_account_email_key", "auth_account", type_="unique")
    op.drop_column("auth_account", "email")


def downgrade() -> None:
    """Downgrade schema: вернуть поле email вместо identifier."""
    # Восстанавливаем поле email
    op.add_column("auth_account", sa.Column("email", sa.String(255), nullable=True))
    
    # Конвертируем обратно (только для email)
    op.execute("""
        UPDATE auth_account 
        SET email = identifier
        WHERE identifier_type = 'email'
    """)
    
    # Делаем email NOT NULL
    op.alter_column("auth_account", "email", nullable=False)
    
    # Создаем индекс и уникальность на email
    op.create_unique_constraint("auth_account_email_key", "auth_account", ["email"])
    op.create_index("ix_auth_account_email", "auth_account", ["email"])
    
    # Удаляем новые поля
    op.drop_index("ix_auth_account_identifier", "auth_account", if_exists=True)
    op.drop_constraint("auth_account_identifier_key", "auth_account", type_="unique")
    op.drop_column("auth_account", "identifier_type")
    op.drop_column("auth_account", "identifier")
