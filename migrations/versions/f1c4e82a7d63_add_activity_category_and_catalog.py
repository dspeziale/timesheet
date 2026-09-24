"""add activity category and seed the auto-fill catalog

Revision ID: f1c4e82a7d63
Revises: e3a7c05f9b21
Create Date: 2026-09-24 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1c4e82a7d63'
down_revision = 'e3a7c05f9b21'
branch_labels = None
depends_on = None

# Catalogo iniziale della compilazione automatica, diviso per area.
CATALOGO = [
    ('Sviluppo', 'Sviluppo e manutenzione evolutiva dei moduli applicativi'),
    ('Sviluppo', 'Analisi funzionale e stesura della documentazione tecnica'),
    ('Sviluppo', 'Sviluppo di API REST e integrazione con servizi esterni'),
    ('Sviluppo', 'Refactoring del codice e ottimizzazione delle performance'),
    ('Sviluppo', 'Esecuzione di test unitari e di integrazione'),
    ('Sviluppo', 'Analisi dei requisiti con il cliente e stima delle attività'),
    ('Sviluppo', 'Code review e supporto tecnico al team di sviluppo'),

    ('Manutenzione', 'Correzione anomalie e attività di bug fixing'),
    ('Manutenzione', 'Manutenzione correttiva sulle procedure in esercizio'),
    ('Manutenzione', 'Aggiornamento delle librerie e gestione delle dipendenze'),
    ('Manutenzione', 'Ottimizzazione delle query e manutenzione della base dati'),
    ('Manutenzione', 'Adeguamento delle procedure a nuove specifiche'),
    ('Manutenzione', 'Bonifica dei dati e verifica di congruenza degli archivi'),

    ('Esercizio', 'Monitoraggio dei sistemi e controllo delle elaborazioni'),
    ('Esercizio', 'Presidio applicativo e gestione delle segnalazioni'),
    ('Esercizio', 'Supporto specialistico e troubleshooting in produzione'),
    ('Esercizio', 'Deploy in ambiente di collaudo e verifica del rilascio'),
    ('Esercizio', 'Configurazione della pipeline CI/CD e automazione dei rilasci'),
    ('Esercizio', 'Verifica dei backup e delle procedure di ripristino'),
    ('Esercizio', 'Riunione di allineamento e pianificazione delle attività'),
]


def _colonne(tabella):
    return {c['name'] for c in sa.inspect(op.get_bind()).get_columns(tabella)}


def upgrade():
    if 'categoria' not in _colonne('activities'):
        with op.batch_alter_table('activities', schema=None) as batch_op:
            batch_op.add_column(sa.Column('categoria', sa.String(32),
                                          server_default=''))

    # Precarica il catalogo saltando le descrizioni gia' presenti: il nome e'
    # unique, e alcune di queste voci possono essere state create a mano dal
    # form del timesheet. In quel caso si limita ad assegnare la categoria.
    bind = op.get_bind()
    for categoria, descrizione in CATALOGO:
        esistente = bind.execute(
            sa.text('SELECT id, categoria FROM activities WHERE name = :n'),
            {'n': descrizione}).fetchone()
        if esistente is None:
            bind.execute(
                sa.text('INSERT INTO activities (name, active, categoria) '
                        'VALUES (:n, :a, :c)'),
                {'n': descrizione, 'a': True, 'c': categoria})
        elif not (esistente[1] or '').strip():
            bind.execute(
                sa.text('UPDATE activities SET categoria = :c WHERE id = :i'),
                {'c': categoria, 'i': esistente[0]})


def downgrade():
    # Le attivita' precaricate si rimuovono solo se nessun timesheet le usa
    bind = op.get_bind()
    for _, descrizione in CATALOGO:
        bind.execute(sa.text(
            'DELETE FROM activities WHERE name = :n AND id NOT IN '
            '(SELECT activity_id FROM timesheets WHERE activity_id IS NOT NULL)'
        ), {'n': descrizione})

    if 'categoria' in _colonne('activities'):
        with op.batch_alter_table('activities', schema=None) as batch_op:
            batch_op.drop_column('categoria')
