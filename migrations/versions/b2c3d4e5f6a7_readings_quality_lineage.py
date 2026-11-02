"""readings_quality_lineage

Revision ID: b2c3d4e5f6a7
Revises: b1c2d3e4f5a6
Create Date: 2026-11-01 18:31:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sensors", sa.Column("display_name", sa.String(length=255), nullable=True))
    op.add_column(
        "sensors",
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="desconocido"),
    )
    op.add_column("sensors", sa.Column("location_note", sa.Text(), nullable=True))
    op.add_column(
        "sensors",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.add_column("gas_readings", sa.Column("value_canonical", sa.Numeric(18, 6), nullable=True))
    op.add_column("gas_readings", sa.Column("unit_canonical", sa.String(length=32), nullable=True))
    op.add_column(
        "gas_readings",
        sa.Column("quality_status", sa.String(length=16), nullable=False, server_default="ok"),
    )
    op.execute(
        """
        UPDATE gas_readings
        SET value_canonical = leyendo,
            unit_canonical = unidad
        WHERE value_canonical IS NULL
        """
    )
    op.execute(
        """
        DELETE FROM gas_readings a
        USING gas_readings b
        WHERE a.sensor_id = b.sensor_id
          AND a.tiempo_inicio = b.tiempo_inicio
          AND a.id > b.id
        """
    )
    op.drop_index("ix_gas_readings_sensor_tiempo", table_name="gas_readings")
    op.create_unique_constraint(
        "uq_gas_readings_sensor_tiempo", "gas_readings", ["sensor_id", "tiempo_inicio"]
    )
    op.create_index(
        "ix_gas_readings_sensor_tiempo_desc",
        "gas_readings",
        ["sensor_id", sa.text("tiempo_inicio DESC")],
    )

    op.create_table(
        "etl_run_steps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("etl_run_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(length=8), nullable=False),
        sa.Column("rows_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["etl_run_id"], ["etl_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_etl_run_steps_etl_run_id", "etl_run_steps", ["etl_run_id"])
    op.create_table(
        "data_quality_issues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gas_reading_id", sa.Integer(), nullable=True),
        sa.Column("sensor_id", sa.Integer(), nullable=True),
        sa.Column("etl_run_id", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="advertencia"),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["gas_reading_id"], ["gas_readings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["etl_run_id"], ["etl_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_quality_issues_code", "data_quality_issues", ["code"])
    op.create_index("ix_data_quality_issues_sensor_id", "data_quality_issues", ["sensor_id"])
    op.create_index("ix_data_quality_issues_etl_run_id", "data_quality_issues", ["etl_run_id"])
    op.create_index(
        "ix_data_quality_issues_gas_reading_id", "data_quality_issues", ["gas_reading_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_data_quality_issues_gas_reading_id", table_name="data_quality_issues")
    op.drop_index("ix_data_quality_issues_etl_run_id", table_name="data_quality_issues")
    op.drop_index("ix_data_quality_issues_sensor_id", table_name="data_quality_issues")
    op.drop_index("ix_data_quality_issues_code", table_name="data_quality_issues")
    op.drop_table("data_quality_issues")
    op.drop_index("ix_etl_run_steps_etl_run_id", table_name="etl_run_steps")
    op.drop_table("etl_run_steps")
    op.drop_index("ix_gas_readings_sensor_tiempo_desc", table_name="gas_readings")
    op.drop_constraint("uq_gas_readings_sensor_tiempo", "gas_readings", type_="unique")
    op.create_index(
        "ix_gas_readings_sensor_tiempo", "gas_readings", ["sensor_id", "tiempo_inicio"]
    )
    op.drop_column("gas_readings", "quality_status")
    op.drop_column("gas_readings", "unit_canonical")
    op.drop_column("gas_readings", "value_canonical")
    op.drop_column("sensors", "is_active")
    op.drop_column("sensors", "location_note")
    op.drop_column("sensors", "kind")
    op.drop_column("sensors", "display_name")
