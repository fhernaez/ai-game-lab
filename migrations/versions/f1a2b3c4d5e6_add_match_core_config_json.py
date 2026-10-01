"""add match core_config_json

Revision ID: f1a2b3c4d5e6
Revises: d0cdb08b0ad3
Create Date: 2026-09-30 21:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'd0cdb08b0ad3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.add_column(sa.Column('core_config_json', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_column('core_config_json')
