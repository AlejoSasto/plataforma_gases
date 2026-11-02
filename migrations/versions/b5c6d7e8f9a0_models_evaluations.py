"""models_evaluations

Revision ID: b5c6d7e8f9a0
Revises: b4c5d6e7f8a9
Create Date: 2026-11-01 18:34:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "model_registry",
        sa.Column("family", sa.String(length=32), nullable=False, server_default="tabular"),
    )
    op.add_column(
        "model_registry",
        sa.Column("problem_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "model_registry",
        sa.Column("calibration", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "model_registry",
        sa.Column("selection_score", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_model_registry_family", "model_registry", ["family"])
    op.create_table(
        "model_evaluations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("fold_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fold_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("gas_code", sa.String(length=10), nullable=False),
        sa.Column("horizon_min", sa.Integer(), nullable=False),
        sa.Column("forecast_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("event_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_final_test", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["model_id"], ["model_registry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_evaluations_model_id", "model_evaluations", ["model_id"])
    op.create_index("ix_model_evaluations_gas_code", "model_evaluations", ["gas_code"])


def downgrade() -> None:
    op.drop_index("ix_model_evaluations_gas_code", table_name="model_evaluations")
    op.drop_index("ix_model_evaluations_model_id", table_name="model_evaluations")
    op.drop_table("model_evaluations")
    op.drop_index("ix_model_registry_family", table_name="model_registry")
    op.drop_column("model_registry", "selection_score")
    op.drop_column("model_registry", "calibration")
    op.drop_column("model_registry", "problem_spec")
    op.drop_column("model_registry", "family")
