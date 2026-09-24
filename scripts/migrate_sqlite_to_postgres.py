#!/usr/bin/env python
"""Copia i dati da un database SQLite al PostgreSQL di destinazione.

Lo schema di destinazione deve gia' esistere e essere aggiornato: ci pensa
`flask db upgrade`, che il container esegue da solo all'avvio. Questo script
sposta soltanto i dati.

Il sorgente non viene modificato. Se il SQLite e' fermo a una revision piu'
vecchia (gli mancano colonne aggiunte in seguito), vengono copiate solo le
colonne presenti in entrambi: le altre restano al default di PostgreSQL.

Uso:
    python scripts/migrate_sqlite_to_postgres.py \
        --source app.db \
        --target "postgres://utente:password@host:5432/dbname"

Il target si puo' anche lasciare all'ambiente (DATABASE_URL). Con --dry-run
non scrive nulla e mostra solo cosa farebbe.
"""
import argparse
import os
import sys

from sqlalchemy import create_engine, select, text

# Consente di lanciare lo script dalla root del progetto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db  # noqa: E402
from app import models  # noqa: F401,E402  (registra i modelli sui metadata)

# alembic_version appartiene alla destinazione: la gestisce Alembic, non noi.
SKIP_TABLES = {'alembic_version'}


def normalizza_url(url):
    """SQLAlchemy 2 non accetta lo schema postgres:// usato da Coolify/Heroku."""
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql://', 1)
    return url


def colonne_esistenti(engine, tabella):
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if tabella not in inspector.get_table_names():
        return None
    return {c['name'] for c in inspector.get_columns(tabella)}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source', default='app.db',
                        help='file SQLite di partenza (default: app.db)')
    parser.add_argument('--target', default=os.environ.get('DATABASE_URL'),
                        help='URL PostgreSQL di destinazione (default: $DATABASE_URL)')
    parser.add_argument('--truncate', action='store_true',
                        help='svuota le tabelle di destinazione prima di copiare')
    parser.add_argument('--dry-run', action='store_true',
                        help='mostra cosa verrebbe copiato senza scrivere')
    args = parser.parse_args()

    if not args.target:
        parser.error('serve --target oppure la variabile DATABASE_URL')
    if not os.path.exists(args.source):
        parser.error('file sorgente non trovato: %s' % args.source)

    target_url = normalizza_url(args.target)
    if not target_url.startswith('postgresql'):
        parser.error('la destinazione non e\' un database PostgreSQL: %s' % target_url)

    src = create_engine('sqlite:///' + os.path.abspath(args.source))
    dst = create_engine(target_url)

    # I metadata dell'app ordinano gia' le tabelle rispettando le foreign key
    tabelle = [t for t in db.metadata.sorted_tables if t.name not in SKIP_TABLES]

    print('Sorgente:    %s' % os.path.abspath(args.source))
    print('Destinazione: %s' % target_url.split('@')[-1])
    print()

    with src.connect() as sconn, dst.begin() as dconn:
        # 1) Controlli preliminari: schema presente e tabelle vuote
        problemi = []
        piano = []
        for tabella in tabelle:
            col_src = colonne_esistenti(src, tabella.name)
            col_dst = colonne_esistenti(dst, tabella.name)

            if col_dst is None:
                problemi.append('la tabella "%s" non esiste nella destinazione: '
                                'lancia prima `flask db upgrade`' % tabella.name)
                continue
            if col_src is None:
                piano.append((tabella, [], 0, 'assente nel sorgente, saltata'))
                continue

            comuni = [c.name for c in tabella.columns
                      if c.name in col_src and c.name in col_dst]
            mancanti = sorted(col_src - set(comuni))
            righe = sconn.execute(
                text('SELECT COUNT(*) FROM "%s"' % tabella.name)).scalar()

            presenti = dconn.execute(
                text('SELECT COUNT(*) FROM "%s"' % tabella.name)).scalar()
            if presenti and not args.truncate:
                problemi.append('la tabella "%s" contiene gia\' %d righe: '
                                'usa --truncate per sovrascriverle'
                                % (tabella.name, presenti))

            nota = ''
            if mancanti:
                nota = 'colonne ignorate: %s' % ', '.join(mancanti)
            piano.append((tabella, comuni, righe, nota))

        for tabella, comuni, righe, nota in piano:
            print('  %-16s %4d righe  %s' % (tabella.name, righe, nota))
        print()

        if problemi:
            print('Impossibile procedere:')
            for p in problemi:
                print('  - %s' % p)
            return 1

        if args.dry_run:
            print('--dry-run: nessuna scrittura effettuata.')
            return 0

        # 2) Svuotamento opzionale, in ordine inverso per non violare le FK
        if args.truncate:
            for tabella in reversed(tabelle):
                if colonne_esistenti(dst, tabella.name) is not None:
                    dconn.execute(text('DELETE FROM "%s"' % tabella.name))
            print('Tabelle di destinazione svuotate.')

        # 3) Copia vera e propria
        totale = 0
        for tabella, comuni, righe, _ in piano:
            if not comuni or not righe:
                continue
            colonne = [tabella.c[n] for n in comuni]
            # Si legge con i tipi dei modelli: SQLAlchemy converte da solo le
            # date e i booleani che SQLite memorizza come testo e come 0/1.
            risultati = sconn.execute(select(*colonne)).mappings().all()
            if risultati:
                dconn.execute(tabella.insert(), [dict(r) for r in risultati])
            print('  %-16s %4d righe copiate' % (tabella.name, len(risultati)))
            totale += len(risultati)

        # 4) Riallineamento delle sequenze: senza questo il primo inserimento
        #    dall'app riuserebbe un id gia' occupato e fallirebbe.
        print()
        for tabella in tabelle:
            if 'id' not in tabella.c or colonne_esistenti(dst, tabella.name) is None:
                continue
            seq = dconn.execute(
                text("SELECT pg_get_serial_sequence(:t, 'id')"),
                {'t': tabella.name}).scalar()
            if not seq:
                continue
            nuovo = dconn.execute(text(
                'SELECT setval(:s, COALESCE((SELECT MAX(id) FROM "%s"), 0) + 1, false)'
                % tabella.name), {'s': seq}).scalar()
            print('  sequenza %-22s -> prossimo id %s' % (tabella.name, nuovo))

        print()
        print('Fatto: %d righe copiate.' % totale)

    return 0


if __name__ == '__main__':
    sys.exit(main())
