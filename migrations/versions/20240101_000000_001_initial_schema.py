"""Initial schema creation.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create uuid extension if not exists
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create technologies table
    op.create_table(
        'technologies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=True),
        sa.Column('university', sa.String(100), nullable=False),
        sa.Column('tech_id', sa.String(200), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('scraped_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('top_field', sa.String(100), nullable=True),
        sa.Column('subfield', sa.String(100), nullable=True),
        sa.Column('patent_geography', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('keywords', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('classification_status', sa.String(50), nullable=True, default='pending'),
        sa.Column('classification_confidence', sa.DECIMAL(3, 2), nullable=True),
        sa.Column('last_classified_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )

    # Create indexes for technologies
    op.create_index('idx_technologies_university', 'technologies', ['university'])
    op.create_index('idx_technologies_top_field', 'technologies', ['top_field'])
    op.create_index('idx_technologies_subfield', 'technologies', ['subfield'])
    op.create_index('idx_technologies_scraped_at', 'technologies', ['scraped_at'])
    op.create_index('idx_technologies_classification_status', 'technologies', ['classification_status'])
    op.create_index('idx_technologies_university_tech_id', 'technologies', ['university', 'tech_id'], unique=True)

    # Create universities table
    op.create_table(
        'universities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(20), nullable=False),
        sa.Column('base_url', sa.Text(), nullable=False),
        sa.Column('scraper_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_scraped', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_technologies', sa.Integer(), default=0, nullable=True),
        sa.Column('active', sa.Boolean(), default=True, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code'),
    )

    # Create scrape_logs table
    op.create_table(
        'scrape_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('university', sa.String(100), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('technologies_found', sa.Integer(), default=0, nullable=True),
        sa.Column('technologies_new', sa.Integer(), default=0, nullable=True),
        sa.Column('technologies_updated', sa.Integer(), default=0, nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create classification_logs table
    op.create_table(
        'classification_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('technology_id', sa.Integer(), nullable=True),
        sa.Column('classified_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('top_field', sa.String(100), nullable=True),
        sa.Column('subfield', sa.String(100), nullable=True),
        sa.Column('confidence', sa.DECIMAL(3, 2), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_cost', sa.DECIMAL(10, 6), nullable=True),
        sa.Column('raw_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['technology_id'], ['technologies.id'], ondelete='CASCADE'),
    )

    # Create index on classification_logs
    op.create_index('idx_classification_logs_technology_id', 'classification_logs', ['technology_id'])


def downgrade() -> None:
    op.drop_table('classification_logs')
    op.drop_table('scrape_logs')
    op.drop_table('universities')
    op.drop_index('idx_technologies_university_tech_id', table_name='technologies')
    op.drop_index('idx_technologies_classification_status', table_name='technologies')
    op.drop_index('idx_technologies_scraped_at', table_name='technologies')
    op.drop_index('idx_technologies_subfield', table_name='technologies')
    op.drop_index('idx_technologies_top_field', table_name='technologies')
    op.drop_index('idx_technologies_university', table_name='technologies')
    op.drop_table('technologies')
