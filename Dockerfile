FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=run.py \
    APP_PORT=8000

WORKDIR /app

# libpq5 serve a psycopg2, curl all'healthcheck del container
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 curl \
 && rm -rf /var/lib/apt/lists/*

# I requirements si copiano da soli per sfruttare la cache dei layer:
# il reinstall avviene solo quando cambiano davvero.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Utente non privilegiato
RUN chmod +x docker-entrypoint.sh \
 && useradd --create-home --uid 10001 app \
 && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${APP_PORT:-8000}/healthz" || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
