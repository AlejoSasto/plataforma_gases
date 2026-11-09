"""plan25 instruments, thresholds, benchmark

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-11-07 20:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("serial", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_to", sa.String(length=255), nullable=True),
        sa.Column("site_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("serial"),
    )
    op.create_index("ix_instruments_serial", "instruments", ["serial"])
    op.create_index("ix_instruments_site_id", "instruments", ["site_id"])
    op.add_column("sensors", sa.Column("instrument_id", sa.Integer(), nullable=True))
    op.create_index("ix_sensors_instrument_id", "sensors", ["instrument_id"])
    op.create_foreign_key(
        "fk_sensors_instrument_id",
        "sensors",
        "instruments",
        ["instrument_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "user_instrument_scopes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "instrument_id", name="uq_user_instrument_scope"),
    )
    op.create_index("ix_user_instrument_scopes_user_id", "user_instrument_scopes", ["user_id"])
    op.create_index(
        "ix_user_instrument_scopes_instrument_id", "user_instrument_scopes", ["instrument_id"]
    )
    op.add_column(
        "normative_thresholds",
        sa.Column("metric", sa.String(length=16), nullable=False, server_default="instantaneo"),
    )
    op.add_column(
        "normative_thresholds",
        sa.Column("site_kind", sa.String(length=16), nullable=False, server_default="cualquiera"),
    )
    op.add_column(
        "normative_thresholds",
        sa.Column("kind", sa.String(length=24), nullable=False, server_default="normativo"),
    )
    op.add_column(
        "normative_thresholds",
        sa.Column("article", sa.Text(), nullable=False, server_default=""),
    )
    op.drop_constraint("uq_threshold_gas_level_from", "normative_thresholds", type_="unique")
    op.create_unique_constraint(
        "uq_threshold_gas_level_metric_from",
        "normative_thresholds",
        ["gas_code", "level", "metric", "direction", "site_kind", "valid_from"],
    )
    op.add_column("reading_grid", sa.Column("twa_8h", sa.Numeric(18, 6), nullable=True))
    op.add_column("reading_grid", sa.Column("stel_15min", sa.Numeric(18, 6), nullable=True))
    op.add_column(
        "alerts",
        sa.Column("origin", sa.String(length=16), nullable=False, server_default="en_vivo"),
    )
    op.add_column(
        "alerts",
        sa.Column("human_handled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column("alerts", sa.Column("closed_by", sa.String(length=32), nullable=True))
    op.create_index("ix_alerts_origin", "alerts", ["origin"])
    op.create_table(
        "benchmark_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=True),
        sa.Column("data_hash", sa.String(length=64), nullable=True),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("g1_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("is_final_test", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("selection_report", sa.Text(), nullable=True),
        sa.Column("promoted_algorithm", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "backtest_forecasts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("model_key", sa.String(length=64), nullable=False),
        sa.Column("fold_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sensor_id", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon_min", sa.Integer(), nullable=False),
        sa.Column("q10", sa.Float(), nullable=True),
        sa.Column("q50", sa.Float(), nullable=True),
        sa.Column("q90", sa.Float(), nullable=True),
        sa.Column("q95", sa.Float(), nullable=True),
        sa.Column("y_true", sa.Float(), nullable=True),
        sa.Column("decided_level", sa.String(length=16), nullable=True),
        sa.Column("train_end", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["benchmark_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "model_key",
            "fold_index",
            "sensor_id",
            "issued_at",
            "horizon_min",
            name="uq_backtest_point",
        ),
    )
    op.create_index("ix_backtest_forecasts_run_id", "backtest_forecasts", ["run_id"])
    op.create_index("ix_backtest_forecasts_model_key", "backtest_forecasts", ["model_key"])
    op.create_index("ix_backtest_forecasts_sensor_id", "backtest_forecasts", ["sensor_id"])


def downgrade() -> None:
    op.drop_index("ix_backtest_forecasts_sensor_id", table_name="backtest_forecasts")
    op.drop_index("ix_backtest_forecasts_model_key", table_name="backtest_forecasts")
    op.drop_index("ix_backtest_forecasts_run_id", table_name="backtest_forecasts")
    op.drop_table("backtest_forecasts")
    op.drop_table("benchmark_runs")
    op.drop_index("ix_alerts_origin", table_name="alerts")
    op.drop_column("alerts", "closed_by")
    op.drop_column("alerts", "human_handled")
    op.drop_column("alerts", "origin")
    op.drop_column("reading_grid", "stel_15min")
    op.drop_column("reading_grid", "twa_8h")
    op.execute(
        """
        DELETE FROM normative_thresholds a
        USING normative_thresholds b
        WHERE a.id > b.id
          AND a.gas_code = b.gas_code
          AND a.level = b.level
          AND a.valid_from = b.valid_from
        """
    )
    op.drop_constraint(
        "uq_threshold_gas_level_metric_from", "normative_thresholds", type_="unique"
    )
    op.drop_column("normative_thresholds", "article")
    op.drop_column("normative_thresholds", "kind")
    op.drop_column("normative_thresholds", "site_kind")
    op.drop_column("normative_thresholds", "metric")
    op.create_unique_constraint(
        "uq_threshold_gas_level_from",
        "normative_thresholds",
        ["gas_code", "level", "valid_from"],
    )
    op.drop_index("ix_user_instrument_scopes_instrument_id", table_name="user_instrument_scopes")
    op.drop_index("ix_user_instrument_scopes_user_id", table_name="user_instrument_scopes")
    op.drop_table("user_instrument_scopes")
    op.drop_constraint("fk_sensors_instrument_id", "sensors", type_="foreignkey")
    op.drop_index("ix_sensors_instrument_id", table_name="sensors")
    op.drop_column("sensors", "instrument_id")
    op.drop_index("ix_instruments_site_id", table_name="instruments")
    op.drop_index("ix_instruments_serial", table_name="instruments")
    op.drop_table("instruments")
