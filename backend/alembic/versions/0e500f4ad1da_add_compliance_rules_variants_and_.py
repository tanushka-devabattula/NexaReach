"""add_compliance_rules_variants_and_campaign_contents

Revision ID: 0e500f4ad1da
Revises: 54c0d5dbc30b
Create Date: 2026-10-24 22:59:42.053329

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e500f4ad1da'
down_revision: Union[str, Sequence[str], None] = '54c0d5dbc30b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create compliance_rules table
    op.create_table(
        'compliance_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('pattern', sa.String(length=255), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=True),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='error'),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compliance_rules_id'), 'compliance_rules', ['id'], unique=False)

    # 2. Create content_variants table
    op.create_table(
        'content_variants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('segment_id', sa.Integer(), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=False, server_default='English'),
        sa.Column('variant_text', sa.Text(), nullable=False),
        sa.Column('sample_audience_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
        sa.ForeignKeyConstraint(['segment_id'], ['segments.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_variants_id'), 'content_variants', ['id'], unique=False)

    # 3. Create campaign_contents table
    op.create_table(
        'campaign_contents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=False, server_default='English'),
        sa.Column('segment_id', sa.Integer(), nullable=True),
        sa.Column('channel', sa.String(length=50), nullable=False, server_default='SMS'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
        sa.ForeignKeyConstraint(['segment_id'], ['segments.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_campaign_contents_id'), 'campaign_contents', ['id'], unique=False)

    # 4. Alter translation_records table (using batch_alter_table for SQLite compatibility)
    with op.batch_alter_table('translation_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('campaign_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('message_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.String(length=50), nullable=True, server_default='Auto-translated'))
        batch_op.create_foreign_key('fk_translation_records_campaign', 'campaigns', ['campaign_id'], ['id'])
        batch_op.create_foreign_key('fk_translation_records_message', 'messages', ['message_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('translation_records', schema=None) as batch_op:
        batch_op.drop_constraint('fk_translation_records_message', type_='foreignkey')
        batch_op.drop_constraint('fk_translation_records_campaign', type_='foreignkey')
        batch_op.drop_column('status')
        batch_op.drop_column('message_id')
        batch_op.drop_column('campaign_id')

    op.drop_index(op.f('ix_campaign_contents_id'), table_name='campaign_contents')
    op.drop_table('campaign_contents')
    op.drop_index(op.f('ix_content_variants_id'), table_name='content_variants')
    op.drop_table('content_variants')
    op.drop_index(op.f('ix_compliance_rules_id'), table_name='compliance_rules')
    op.drop_table('compliance_rules')
