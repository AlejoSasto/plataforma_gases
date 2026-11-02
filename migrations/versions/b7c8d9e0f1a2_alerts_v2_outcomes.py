"""alerts_v2_outcomes

Revision ID: b7c8d9e0f1a2
Revises: b6c7d8e9f0a1
Create Date: 2026-11-01 18:36:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("forecast_id", sa.Integer(), nullable=True))
    op.add_column(
        "alerts",
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="confirmado"),
    )
    op.add_column("alerts", sa.Column("threshold_id", sa.Integer(), nullable=True))
    op.add_column("alerts", sa.Column("expected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("alerts", sa.Column("plain_message", sa.Text(), nullable=True))
    op.add_column("alerts", sa.Column("plain_recommendation", sa.Text(), nullable=True))
    op.add_column("alerts", sa.Column("resolved_by", sa.Integer(), nullable=True))
    op.create_index("ix_alerts_forecast_id", "alerts", ["forecast_id"])
    op.create_index("ix_alerts_kind", "alerts", ["kind"])
    op.create_foreign_key(
        "fk_alerts_forecast_id", "alerts", "forecasts", ["forecast_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_alerts_threshold_id",
        "alerts",
        "normative_thresholds",
        ["threshold_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_alerts_resolved_by", "alerts", "users", ["resolved_by"], ["id"], ondelete="SET NULL"
    )
    op.execute(
        """
        UPDATE alerts
        SET kind = 'confirmado'
        WHERE kind IS NULL OR kind = ''
        """
    )
    op.execute(
        """
        UPDATE alerts
        SET plain_message = message,
            plain_recommendation = recommendation
        WHERE plain_message IS NULL
        """
    )
    op.create_table(
        "alert_outcomes",
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False, server_default="pendiente"),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("lead_minutes", sa.Float(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["threshold_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("alert_id"),
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW missed_events_v AS
        SELECT e.id AS event_id,
               e.sensor_id,
               e.gas_code,
               e.level,
               e.started_at,
               e.ended_at
        FROM threshold_events e
        WHERE NOT EXISTS (
            SELECT 1
            FROM alert_outcomes o
            WHERE o.event_id = e.id
              AND o.outcome = 'acertado'
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS missed_events_v")
    op.drop_table("alert_outcomes")
    op.drop_constraint("fk_alerts_resolved_by", "alerts", type_="foreignkey")
    op.drop_constraint("fk_alerts_threshold_id", "alerts", type_="foreignkey")
    op.drop_constraint("fk_alerts_forecast_id", "alerts", type_="foreignkey")
    op.drop_index("ix_alerts_kind", table_name="alerts")
    op.drop_index("ix_alerts_forecast_id", table_name="alerts")
    op.drop_column("alerts", "resolved_by")
    op.drop_column("alerts", "plain_recommendation")
    op.drop_column("alerts", "plain_message")
    op.drop_column("alerts", "expected_at")
    op.drop_column("alerts", "threshold_id")
    op.drop_column("alerts", "kind")
    op.drop_column("alerts", "forecast_id")
