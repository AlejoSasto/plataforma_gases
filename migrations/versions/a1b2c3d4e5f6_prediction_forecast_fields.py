"""prediction_forecast_fields

Revision ID: a1b2c3d4e5f6
Revises: 51e28c39eed2
Create Date: 2026-09-20 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "51e28c39eed2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "predictions",
        sa.Column("predicted_concentration", sa.Float(), nullable=True),
    )
    op.add_column(
        "predictions",
        sa.Column("horizon_minutes", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("predictions", "horizon_minutes")
    op.drop_column("predictions", "predicted_concentration")
