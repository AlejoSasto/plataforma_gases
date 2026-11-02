"""access_v3 totp backups and invitation sites

Revision ID: c1d2e3f4a5b6
Revises: b9d0e1f2a3b4
Create Date: 2026-11-01 19:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_backup_hashes", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("user_invitations", sa.Column("site_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("user_invitations", sa.Column("full_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("user_invitations", "full_name")
    op.drop_column("user_invitations", "site_ids")
    op.drop_column("users", "totp_backup_hashes")
