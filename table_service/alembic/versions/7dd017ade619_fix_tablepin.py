"""fix TablePin

Revision ID: 7dd017ade619
Revises: a1e02152a4da
Create Date: 2026-07-14 19:35:32.378581

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7dd017ade619"
down_revision: Union[str, Sequence[str], None] = "a1e02152a4da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "table_pins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column(
            "pinned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["table_id"], ["data_tables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],  # ← Проверьте название таблицы пользователей
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "table_id", name="uq_table_pins_user_table"),
    )
    op.create_index("ix_table_pins_id", "table_pins", ["id"], unique=False)
    op.create_index("ix_table_pins_user_id", "table_pins", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_table_pins_user_id", table_name="table_pins")
    op.drop_index("ix_table_pins_id", table_name="table_pins")
    op.drop_table("table_pins")
