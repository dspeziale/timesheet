"""add per-entry trasferta expense fields to timesheets

Revision ID: d8f2b6c1e440
Revises: c7e1a9b4d2f8
Create Date: 2026-09-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8f2b6c1e440'
down_revision = 'c7e1a9b4d2f8'
branch_labels = None
depends_on = None

COLUMNS = ('trasferta_transport', 'trasferta_meal', 'trasferta_extra')


def _existing_columns():
    """Colonne gia' presenti sulla tabella timesheets.

    In produzione possono essere state aggiunte all'avvio da
    _sync_missing_columns(): la migration resta applicabile anche in quel caso.
    """
    bind = op.get_bind()
    return {c['name'] for c in sa.inspect(bind).get_columns('timesheets')}


def _backfill_from_projects():
    """Le giornate gia' marcate come trasferta ereditano gli importi della loro
    commessa, cosi' non restano a zero dopo il passaggio a importi per voce.

    Tocca solo le righe ancora completamente a zero: eventuali importi gia'
    confermati a mano non vengono sovrascritti, e la migration resta ripetibile.
    """
    op.execute(sa.text("""
        UPDATE timesheets SET
            trasferta_transport = COALESCE((SELECT p.trasferta_transport FROM projects p
                                            WHERE p.id = timesheets.project_id), 0),
            trasferta_meal = COALESCE((SELECT p.trasferta_meal FROM projects p
                                       WHERE p.id = timesheets.project_id), 0),
            trasferta_extra = COALESCE((SELECT p.trasferta_extra FROM projects p
                                        WHERE p.id = timesheets.project_id), 0)
        WHERE is_trasferta
          AND project_id IS NOT NULL
          AND trasferta_transport = 0
          AND trasferta_meal = 0
          AND trasferta_extra = 0
    """))


def upgrade():
    present = _existing_columns()
    missing = [c for c in COLUMNS if c not in present]
    if missing:
        with op.batch_alter_table('timesheets', schema=None) as batch_op:
            for name in missing:
                batch_op.add_column(sa.Column(name, sa.Numeric(10, 2),
                                              nullable=False, server_default='0'))
    _backfill_from_projects()


def downgrade():
    present = _existing_columns()
    to_drop = [c for c in reversed(COLUMNS) if c in present]
    if not to_drop:
        return
    with op.batch_alter_table('timesheets', schema=None) as batch_op:
        for name in to_drop:
            batch_op.drop_column(name)
