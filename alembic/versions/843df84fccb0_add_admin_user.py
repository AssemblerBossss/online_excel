"""add_admin_user

Revision ID: 843df84fccb0
Revises: 66bbceeef96e
Create Date: 2025-12-14 16:15:20.086564

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone
from passlib.context import CryptContext 


# revision identifiers, used by Alembic.
revision: str = '843df84fccb0'
down_revision: Union[str, Sequence[str], None] = '66bbceeef96e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    """Add admin user to the database."""
    # Хешируем пароль admin
    hashed_password = pwd_context.hash("admin_password")
    
    # Вставляем админ пользователя с явным приведением типа для role
    op.execute(
        sa.text(
            """
            INSERT INTO users (email, hashed_password, first_name, last_name, role, is_active, created_at)
            VALUES (:email, :hashed_password, :first_name, :last_name, CAST(:role AS userrole), :is_active, :created_at)
            ON CONFLICT (email) DO NOTHING;
            """
        ).bindparams(
            email="admin@example.com",
            hashed_password=hashed_password,
            first_name="Admin",
            last_name="User",
            role="ADMIN", 
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
    )


def downgrade() -> None:
    """Remove admin user from the database."""
    op.execute(
        sa.text(
            """
            DELETE FROM users WHERE email = :email;
            """
        ).bindparams(email="admin@example.com")
    )