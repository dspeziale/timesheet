"""add settings table and customer e-invoicing fields

Revision ID: e3a7c05f9b21
Revises: d8f2b6c1e440
Create Date: 2026-09-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3a7c05f9b21'
down_revision = 'd8f2b6c1e440'
branch_labels = None
depends_on = None

CUSTOMER_COLUMNS = (
    ('sdi_code', sa.String(7), "'0000000'"),
    ('pec', sa.String(120), "''"),
)


def _inspector():
    return sa.inspect(op.get_bind())


def upgrade():
    inspector = _inspector()

    if 'settings' not in inspector.get_table_names():
        op.create_table(
            'settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('denominazione', sa.String(128), server_default=''),
            sa.Column('nome', sa.String(64), server_default=''),
            sa.Column('cognome', sa.String(64), server_default=''),
            sa.Column('partita_iva', sa.String(16), server_default=''),
            sa.Column('codice_fiscale', sa.String(16), server_default=''),
            sa.Column('regime_fiscale', sa.String(8), server_default='RF19'),
            sa.Column('indirizzo', sa.String(256), server_default=''),
            sa.Column('numero_civico', sa.String(16), server_default=''),
            sa.Column('cap', sa.String(8), server_default=''),
            sa.Column('comune', sa.String(128), server_default=''),
            sa.Column('provincia', sa.String(4), server_default=''),
            sa.Column('nazione', sa.String(4), server_default='IT'),
            sa.Column('telefono', sa.String(32), server_default=''),
            sa.Column('email', sa.String(120), server_default=''),
            sa.Column('rea_ufficio', sa.String(8), server_default=''),
            sa.Column('rea_numero', sa.String(32), server_default=''),
            sa.Column('tipo_documento', sa.String(8), server_default='TD01'),
            sa.Column('invoice_prefix', sa.String(16), server_default=''),
            sa.Column('invoice_next_number', sa.Integer(), server_default='1'),
            sa.Column('descrizione_riga', sa.String(256),
                      server_default='Prestazione di servizi di consulenza informatica'),
            sa.Column('descrizione_spese', sa.String(256),
                      server_default='Rimborso spese di trasferta'),
            sa.Column('natura_iva', sa.String(8), server_default='N2.2'),
            sa.Column('riferimento_normativo', sa.Text()),
            sa.Column('bollo_enabled', sa.Boolean(), server_default='1'),
            sa.Column('bollo_importo', sa.Numeric(10, 2), server_default='2.00'),
            sa.Column('bollo_soglia', sa.Numeric(10, 2), server_default='77.47'),
            sa.Column('bollo_a_carico_cliente', sa.Boolean(), server_default='0'),
            sa.Column('rivalsa_inps_percent', sa.Numeric(5, 2), server_default='0'),
            sa.Column('modalita_pagamento', sa.String(8), server_default='MP05'),
            sa.Column('condizioni_pagamento', sa.String(8), server_default='TP02'),
            sa.Column('iban', sa.String(34), server_default=''),
            sa.Column('banca', sa.String(128), server_default=''),
            sa.Column('giorni_scadenza', sa.Integer(), server_default='30'),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_settings')),
        )

    present = {c['name'] for c in inspector.get_columns('customers')}
    missing = [(n, t, d) for n, t, d in CUSTOMER_COLUMNS if n not in present]
    if missing:
        with op.batch_alter_table('customers', schema=None) as batch_op:
            for name, type_, default in missing:
                batch_op.add_column(sa.Column(name, type_, server_default=sa.text(default)))


def downgrade():
    inspector = _inspector()

    present = {c['name'] for c in inspector.get_columns('customers')}
    to_drop = [n for n, _, _ in reversed(CUSTOMER_COLUMNS) if n in present]
    if to_drop:
        with op.batch_alter_table('customers', schema=None) as batch_op:
            for name in to_drop:
                batch_op.drop_column(name)

    if 'settings' in inspector.get_table_names():
        op.drop_table('settings')
