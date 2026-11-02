"""reading_grid_and_events

Revision ID: b4c5d6e7f8a9
Revises: b3c4d5e6f7a8
Create Date: 2026-11-01 18:33:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reading_grid",
        sa.Column("sensor_id", sa.Integer(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=True),
        sa.Column("is_imputed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_missing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source_etl_run_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_etl_run_id"], ["etl_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("sensor_id", "ts"),
        sa.UniqueConstraint("sensor_id", "ts", name="uq_reading_grid_sensor_ts"),
    )
    op.create_table(
        "threshold_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sensor_id", sa.Integer(), nullable=False),
        sa.Column("gas_code", sa.String(length=10), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("threshold_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("peak_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("peak_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detected_by", sa.String(length=16), nullable=False, server_default="etl"),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["threshold_id"], ["normative_thresholds.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_threshold_events_sensor_id", "threshold_events", ["sensor_id"])
    op.create_index("ix_threshold_events_gas_code", "threshold_events", ["gas_code"])


def downgrade() -> None:
    op.drop_index("ix_threshold_events_gas_code", table_name="threshold_events")
    op.drop_index("ix_threshold_events_sensor_id", table_name="threshold_events")
    op.drop_table("threshold_events")
    op.drop_table("reading_grid")
