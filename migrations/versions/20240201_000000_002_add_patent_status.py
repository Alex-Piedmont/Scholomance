"""Add patent status fields.

Revision ID: 002
Revises: 001
Create Date: 2024-02-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add patent status columns to technologies table
    op.add_column(
        'technologies',
        sa.Column('patent_status', sa.String(50), nullable=True, server_default='unknown')
    )
    op.add_column(
        'technologies',
        sa.Column('patent_status_confidence', sa.DECIMAL(3, 2), nullable=True)
    )
    op.add_column(
        'technologies',
        sa.Column('patent_status_source', sa.String(50), nullable=True)
    )
    op.add_column(
        'technologies',
        sa.Column('last_patent_check_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Create index on patent_status for efficient filtering
    op.create_index('idx_technologies_patent_status', 'technologies', ['patent_status'])


def downgrade() -> None:
    # Drop index first
    op.drop_index('idx_technologies_patent_status', table_name='technologies')

    # Drop columns
    op.drop_column('technologies', 'last_patent_check_at')
    op.drop_column('technologies', 'patent_status_source')
    op.drop_column('technologies', 'patent_status_confidence')
    op.drop_column('technologies', 'patent_status')
