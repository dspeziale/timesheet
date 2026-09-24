#!/usr/bin/env python
"""Attende che il database risponda prima di proseguire con l'avvio.

Coolify puo' avviare il container dell'applicazione mentre il PostgreSQL sta
ancora partendo: senza questa attesa il primo tentativo fallisce, il container
esce e il deploy viene dichiarato fallito anche quando la configurazione e'
corretta.

L'attesa e' limitata: superati i tentativi il processo esce con errore, cosi'
un database davvero irraggiungibile non lascia il container appeso. Il
messaggio finale distingue i casi che si sbagliano piu' spesso (nome non
risolto, credenziali errate, porta chiusa) per non costringere a leggere il
traceback di SQLAlchemy.
"""
import os
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

from config import Config

TENTATIVI = int(os.environ.get('DB_WAIT_ATTEMPTS', '30'))
PAUSA = float(os.environ.get('DB_WAIT_INTERVAL', '2'))


def suggerimento(errore):
    """Traduce gli errori di connessione piu' comuni in un'indicazione utile."""
    testo = str(errore).lower()
    if 'name resolution' in testo or 'could not translate host name' in testo:
        return ("L'hostname del database non si risolve. Verifica che il "
                "servizio PostgreSQL sia avviato e che l'hostname in "
                "DATABASE_URL sia quello attuale: cancellando e ricreando il "
                "database in Coolify l'hostname cambia.")
    if 'password authentication failed' in testo:
        return ("Credenziali rifiutate. La password in DATABASE_URL non "
                "coincide con quella del database: la password viene applicata "
                "solo alla prima creazione del volume, quindi quella mostrata "
                "nell'interfaccia puo' essere disallineata. Dal terminale del "
                "database: psql -U postgres -c \"ALTER USER postgres PASSWORD "
                "'...';\"")
    if 'does not exist' in testo:
        return ("Il database indicato non esiste: controlla l'ultima parte "
                "di DATABASE_URL, dopo la porta.")
    if 'connection refused' in testo:
        return ("Connessione rifiutata: l'host risponde ma non c'e' PostgreSQL "
                "in ascolto su quella porta.")
    return None


def main():
    url = make_url(Config.SQLALCHEMY_DATABASE_URI)
    print('[wait-for-db] Database %s@%s:%s/%s'
          % (url.username, url.host, url.port or 5432, url.database), flush=True)

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI,
                           connect_args={'connect_timeout': 5})
    ultimo = None

    for tentativo in range(1, TENTATIVI + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            print('[wait-for-db] Database raggiungibile (tentativo %d).'
                  % tentativo, flush=True)
            return 0
        except Exception as e:  # noqa: BLE001 - qualunque errore e' un retry
            ultimo = e
            if tentativo < TENTATIVI:
                print('[wait-for-db] Tentativo %d/%d fallito, riprovo tra %gs...'
                      % (tentativo, TENTATIVI, PAUSA), flush=True)
                time.sleep(PAUSA)

    print('[wait-for-db] Database non raggiungibile dopo %d tentativi.'
          % TENTATIVI, flush=True)
    causa = getattr(ultimo, 'orig', ultimo)
    print('[wait-for-db] Errore: %s' % str(causa).strip(), flush=True)
    aiuto = suggerimento(ultimo)
    if aiuto:
        print('[wait-for-db] %s' % aiuto, flush=True)
    return 1


if __name__ == '__main__':
    sys.exit(main())
