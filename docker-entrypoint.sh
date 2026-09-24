#!/bin/sh
# Avvio del container: attende il database, allinea lo schema, serve l'app.
#
# A differenza del deploy serverless, qui c'e' un processo di avvio dedicato:
# le migration girano una volta sola, prima dei worker, ed e' questa la via
# ufficiale per aggiornare lo schema.
set -e

python /app/wait_for_db.py

echo "[entrypoint] Applico le migration del database..."
flask db upgrade

echo "[entrypoint] Avvio gunicorn sulla porta ${PORT:-8000}..."
exec gunicorn run:app \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --threads "${WEB_THREADS:-4}" \
    --timeout "${WEB_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
