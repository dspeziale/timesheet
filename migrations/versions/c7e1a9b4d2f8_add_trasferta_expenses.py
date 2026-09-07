"""add trasferta daily expense fields to projects

Revision ID: c7e1a9b4d2f8
Revises: a1b2c3d4e5f6
Create Date: 2026-09-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7e1a9b4d2f8'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('trasferta_transport', sa.Numeric(10, 2),
                                      nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('trasferta_meal', sa.Numeric(10, 2),
                                      nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('trasferta_extra', sa.Numeric(10, 2),
                                      nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('trasferta_extra')
        batch_op.drop_column('trasferta_meal')
        batch_op.drop_column('trasferta_transport')
