"""add TablePin

Revision ID: a1e02152a4da
Revises: ba5eae50baf0
Create Date: 2026-07-14 19:09:11.682029

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1e02152a4da"
down_revision: str | Sequence[str] | None = "ba5eae50baf0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "table_id", name="uq_table_pins_user_table"),
    )
    op.create_index("ix_table_pins_id", "table_pins", ["id"], unique=False)
    op.create_index("ix_table_pins_user_id", "table_pins", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_table_pins_user_id", table_name="table_pins")
    op.drop_index("ix_table_pins_id", table_name="table_pins")
    op.drop_table("table_pins")
