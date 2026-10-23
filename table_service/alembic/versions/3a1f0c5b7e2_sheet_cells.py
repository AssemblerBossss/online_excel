"""sheet_cells: разреженное хранение ячеек вместо table_rows

Revision ID: d3a1f0c5b7e2
Revises: 2c0451adbe8c
Create Date: 2026-10-21 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d3a1f0c5b7e2"
down_revision: str | Sequence[str] | None = "2c0451adbe8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema. Данные table_rows НЕ переносятся (проект учебный)."""
    op.create_table(
        "sheet_cells",
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("row", sa.Integer(), nullable=False),
        sa.Column("col", sa.Integer(), nullable=False),
        sa.Column("raw", sa.Text(), nullable=True),
        sa.Column("value", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("style", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.ForeignKeyConstraint(["table_id"], ["data_tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("table_id", "row", "col"),
    )
    # Сдвиг колонок (вставка/удаление) ищет ячейки по (table_id, col)
    op.create_index("ix_sheet_cells_table_col", "sheet_cells", ["table_id", "col"])

    op.add_column(
        "data_tables",
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "data_tables",
        sa.Column("layout_revision", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "data_tables",
        sa.Column(
            "sheet_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.drop_column("data_tables", "columns_schema")

    op.drop_table("table_rows")


def downgrade() -> None:
    """Downgrade schema. Ячейки не конвертируются обратно в строки."""
    op.create_table(
        "table_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("row_data", sa.JSON(), nullable=False),
        sa.Column("formulas", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["table_id"], ["data_tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_table_rows_id", "table_rows", ["id"])
    op.create_index(
        "ix_table_rows_table_id_created", "table_rows", ["table_id", "created_at"]
    )
    op.create_index(
        "ix_table_rows_table_id_updated", "table_rows", ["table_id", "updated_at"]
    )
    op.add_column(
        "data_tables",
        sa.Column(
            "columns_schema",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )
    op.drop_column("data_tables", "sheet_meta")
    op.drop_column("data_tables", "layout_revision")
    op.drop_column("data_tables", "revision")
    op.drop_index("ix_sheet_cells_table_col", table_name="sheet_cells")
    op.drop_table("sheet_cells")
