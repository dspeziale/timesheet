"""add ferie field and make project_id nullable

Revision ID: a1b2c3d4e5f6
Revises: 607534e0b107
Create Date: 2026-07-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '607534e0b107'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('timesheets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_ferie', sa.Boolean(), nullable=True))
        batch_op.alter_column('project_id',
                              existing_type=sa.Integer(),
                              nullable=True)


def downgrade():
    with op.batch_alter_table('timesheets', schema=None) as batch_op:
        batch_op.alter_column('project_id',
                              existing_type=sa.Integer(),
                              nullable=False)
        batch_op.drop_column('is_ferie')
