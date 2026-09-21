"""reports_table

Revision ID: 51e28c39eed2
Revises: c2be2667ab48
Create Date: 2026-09-20 20:38:47.143022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51e28c39eed2'
down_revision: Union[str, None] = 'c2be2667ab48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('reports',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('type', sa.String(length=64), nullable=False),
    sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
    sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('file_path', sa.String(length=1024), nullable=False),
    sa.Column('generated_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['generated_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_generated_by'), 'reports', ['generated_by'], unique=False)
    op.create_index(op.f('ix_reports_type'), 'reports', ['type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reports_type'), table_name='reports')
    op.drop_index(op.f('ix_reports_generated_by'), table_name='reports')
    op.drop_table('reports')
