"""readings_no_synthetic_check

Revision ID: b3c4d5e6f7a8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-01 18:32:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM gas_readings WHERE is_synthetic = true")
    op.create_check_constraint(
        "ck_gas_readings_no_synthetic",
        "gas_readings",
        "is_synthetic = false",
    )


def downgrade() -> None:
    op.drop_constraint("ck_gas_readings_no_synthetic", "gas_readings", type_="check")
