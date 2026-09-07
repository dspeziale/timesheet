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

COLUMNS = ('trasferta_transport', 'trasferta_meal', 'trasferta_extra')


def _existing_columns():
    """Colonne gia' presenti sulla tabella projects.

    In produzione (Vercel) le colonne possono essere state aggiunte
    automaticamente all'avvio dell'app da _sync_missing_columns(): la migration
    deve restare applicabile anche in quel caso.
    """
    bind = op.get_bind()
    return {c['name'] for c in sa.inspect(bind).get_columns('projects')}


def upgrade():
    present = _existing_columns()
    missing = [c for c in COLUMNS if c not in present]
    if not missing:
        return
    with op.batch_alter_table('projects', schema=None) as batch_op:
        for name in missing:
            batch_op.add_column(sa.Column(name, sa.Numeric(10, 2),
                                          nullable=False, server_default='0'))


def downgrade():
    present = _existing_columns()
    to_drop = [c for c in reversed(COLUMNS) if c in present]
    if not to_drop:
        return
    with op.batch_alter_table('projects', schema=None) as batch_op:
        for name in to_drop:
            batch_op.drop_column(name)
