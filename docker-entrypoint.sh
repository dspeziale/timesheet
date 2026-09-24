#!/bin/sh
# Avvio del container: prima allinea lo schema, poi serve l'app.
#
# A differenza del deploy serverless, qui c'e' un processo di avvio dedicato:
# le migration girano una volta sola, prima dei worker, ed e' questa la via
# ufficiale per aggiornare lo schema (l'allineamento automatico delle colonne
# in create_app resta solo come rete di sicurezza).
set -e

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
