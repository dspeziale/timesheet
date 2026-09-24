#!/bin/sh
# Avvio del container: attende il database, allinea lo schema, serve l'app.
#
# A differenza del deploy serverless, qui c'e' un processo di avvio dedicato:
# le migration girano una volta sola, prima dei worker, ed e' questa la via
# ufficiale per aggiornare lo schema.
set -e

# La porta interna e' APP_PORT, non PORT: alcune piattaforme (Coolify)
# iniettano un PORT proprio, e gunicorn finirebbe in ascolto su una porta
# diversa da quella verso cui il reverse proxy instrada, con un 502
# difficile da spiegare.

python /app/wait_for_db.py

echo "[entrypoint] Applico le migration del database..."
flask db upgrade

echo "[entrypoint] Avvio gunicorn sulla porta ${APP_PORT:-8000}..."
exec gunicorn run:app \
    --bind "0.0.0.0:${APP_PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --threads "${WEB_THREADS:-4}" \
    --timeout "${WEB_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
