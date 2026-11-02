"""drop_predictions

Revision ID: b9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-11-01 18:38:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("alerts_prediction_id_fkey", "alerts", type_="foreignkey")
    op.drop_index("ix_alerts_prediction_id", table_name="alerts")
    op.drop_column("alerts", "prediction_id")
    op.drop_index("ix_predictions_risk_level", table_name="predictions")
    op.drop_index("ix_predictions_model_registry_id", table_name="predictions")
    op.drop_index("ix_predictions_gas_reading_id", table_name="predictions")
    op.drop_table("predictions")


def downgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gas_reading_id", sa.Integer(), nullable=False),
        sa.Column("model_registry_id", sa.Integer(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("predicted_label", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("predicted_concentration", sa.Float(), nullable=True),
        sa.Column("horizon_minutes", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["gas_reading_id"], ["gas_readings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_registry_id"], ["model_registry.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_gas_reading_id", "predictions", ["gas_reading_id"])
    op.create_index("ix_predictions_model_registry_id", "predictions", ["model_registry_id"])
    op.create_index("ix_predictions_risk_level", "predictions", ["risk_level"])
    op.add_column("alerts", sa.Column("prediction_id", sa.Integer(), nullable=True))
    op.create_index("ix_alerts_prediction_id", "alerts", ["prediction_id"])
    op.create_foreign_key(
        "alerts_prediction_id_fkey",
        "alerts",
        "predictions",
        ["prediction_id"],
        ["id"],
        ondelete="SET NULL",
    )
