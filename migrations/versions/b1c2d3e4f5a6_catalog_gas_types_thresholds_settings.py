"""catalog_gas_types_thresholds_settings

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-11-01 18:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gas_types",
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("plain_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("canonical_unit", sa.String(length=32), nullable=False),
        sa.Column("lel_percent_vol", sa.Numeric(8, 4), nullable=True),
        sa.Column("physical_max", sa.Numeric(18, 6), nullable=True),
        sa.Column("max_rate_per_min", sa.Numeric(18, 6), nullable=True),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="99"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "normative_thresholds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gas_code", sa.String(length=10), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False, server_default=""),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["gas_code"], ["gas_types.code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gas_code", "level", "valid_from", name="uq_threshold_gas_level_from"),
    )
    op.create_index("ix_normative_thresholds_gas_code", "normative_thresholds", ["gas_code"])
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_normative_thresholds_gas_code", table_name="normative_thresholds")
    op.drop_table("normative_thresholds")
    op.drop_table("gas_types")
