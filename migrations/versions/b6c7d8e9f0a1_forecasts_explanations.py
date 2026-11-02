"""forecasts_explanations

Revision ID: b6c7d8e9f0a1
Revises: b5c6d7e8f9a0
Create Date: 2026-11-01 18:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, None] = "b5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "forecasts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sensor_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status_level", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("exceed_prob", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.String(length=16), nullable=False, server_default="media"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_id"], ["model_registry.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sensor_id", "model_id", "issued_at", name="uq_forecast_sensor_model_issued"),
    )
    op.create_index("ix_forecasts_sensor_id", "forecasts", ["sensor_id"])
    op.create_index("ix_forecasts_model_id", "forecasts", ["model_id"])
    op.create_index("ix_forecasts_issued_at", "forecasts", ["issued_at"])
    op.create_table(
        "forecast_quantiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("forecast_id", sa.Integer(), nullable=False),
        sa.Column("horizon_min", sa.Integer(), nullable=False),
        sa.Column("q10", sa.Float(), nullable=True),
        sa.Column("q50", sa.Float(), nullable=True),
        sa.Column("q90", sa.Float(), nullable=True),
        sa.Column("q95", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["forecast_id"], ["forecasts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forecast_quantiles_forecast_id", "forecast_quantiles", ["forecast_id"])
    op.create_table(
        "forecast_explanations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("forecast_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=64), nullable=False),
        sa.Column("factors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("plain_text", sa.String(length=2000), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["forecast_id"], ["forecasts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_forecast_explanations_forecast_id", "forecast_explanations", ["forecast_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_forecast_explanations_forecast_id", table_name="forecast_explanations")
    op.drop_table("forecast_explanations")
    op.drop_index("ix_forecast_quantiles_forecast_id", table_name="forecast_quantiles")
    op.drop_table("forecast_quantiles")
    op.drop_index("ix_forecasts_issued_at", table_name="forecasts")
    op.drop_index("ix_forecasts_model_id", table_name="forecasts")
    op.drop_index("ix_forecasts_sensor_id", table_name="forecasts")
    op.drop_table("forecasts")
