# Deploy su Coolify

L'app gira in un container Docker: `gunicorn` serve Flask, e all'avvio
`docker-entrypoint.sh` applica le migration prima di accettare traffico.

## Scegli il percorso

| | Quando usarlo | Build pack Coolify |
|---|---|---|
| **A. Solo Dockerfile** | Il database ce l'hai già fuori (Neon, Supabase, un Postgres tuo) | `Dockerfile` |
| **B. Docker Compose** | Vuoi che Coolify gestisca anche PostgreSQL | `Docker Compose` |

---

## A. Database esterno (Dockerfile)

1. In Coolify: **New Resource → Application → Public/Private Repository**, scegli
   questo repo e il branch `main`.
2. **Build Pack**: `Dockerfile`. Coolify trova da solo il `Dockerfile` nella root.
3. **Port**: `8000`.
4. **Environment Variables** (vedi `.env.example`):

   | Variabile | Valore |
   |---|---|
   | `SECRET_KEY` | **obbligatoria** — genera con `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `DATABASE_URL` | `postgresql://utente:password@host:5432/dbname` |
   | `APP_NAME` | `RoxySheet` (facoltativa) |
   | `TZ` | `Europe/Rome` (facoltativa) |

5. **Health Check Path**: `/healthz`.
6. Assegna il dominio e fai **Deploy**.

## B. PostgreSQL gestito da Coolify (Docker Compose)

1. **New Resource → Application**, stesso repo, **Build Pack**: `Docker Compose`.
2. **Compose file**: `docker-compose.yaml`.
3. Variabili: `SECRET_KEY` e `POSTGRES_PASSWORD` (obbligatorie; il compose si
   rifiuta di partire senza). Facoltative: `POSTGRES_USER`, `POSTGRES_DB`,
   `APP_NAME`, `TZ`, `WEB_CONCURRENCY`.
4. `DATABASE_URL` **non va impostata**: la compone il compose puntando al
   servizio `db`.
5. Esponi il servizio `web` sul dominio e fai **Deploy**.

I dati di Postgres vivono sul volume `pgdata`, che sopravvive ai redeploy.

---

## Dopo il primo deploy

1. Apri `https://tuo-dominio/init-admin` per creare l'utente iniziale
   (`admin` / `admin123`).
2. **Cambia subito la password** da *Profilo Utente*: finché è quella di
   default chiunque conosca l'URL può entrare.
3. Compila **Impostazioni** con i dati della tua azienda.

## Migrare i dati

### Da SQLite (`app.db`) a PostgreSQL

Lo schema sulla destinazione lo crea il container al primo avvio, quindi
**fai prima il deploy** e solo dopo sposta i dati:

```bash
# 1. Guarda cosa verrebbe copiato, senza scrivere nulla
python scripts/migrate_sqlite_to_postgres.py     --source app.db     --target "postgres://utente:password@host:5432/dbname"     --dry-run

# 2. Copia per davvero
python scripts/migrate_sqlite_to_postgres.py     --source app.db     --target "postgres://utente:password@host:5432/dbname"
```

Con il Postgres di Coolify serve la **Postgres URL (public)** e la porta
esposta, perché lo script gira dal tuo PC: la URL interna è raggiungibile solo
dai container. Se preferisci non esporre il database, esegui lo script dentro
il container dell'app (Coolify → *Terminal*) dopo averci copiato `app.db`.

Lo script:

- non tocca il sorgente;
- copia solo le colonne presenti in entrambi i database, quindi funziona anche
  se il SQLite è fermo a una revision più vecchia (le colonne nuove prendono il
  default di PostgreSQL);
- **riallinea le sequenze**: senza quel passaggio il primo inserimento
  dall'app riuserebbe un id già occupato e fallirebbe;
- si rifiuta di partire se la destinazione contiene già dati (`--truncate` per
  sovrascrivere) o se lo schema non è ancora stato creato.

### Da un altro PostgreSQL (es. Neon)

Lo schema è identico, quindi basta un dump:

```bash
pg_dump "$VECCHIO_DATABASE_URL" --no-owner --no-acl -Fc -f timesheet.dump
pg_restore -d "$NUOVO_DATABASE_URL" --no-owner --no-acl timesheet.dump
```

Se invece punti il nuovo container al database Neon già esistente, non serve
fare nulla: `flask db upgrade` vede lo schema già aggiornato e non tocca niente.

## Aggiornamenti

Un push su `main` fa partire il redeploy (se hai attivato l'auto-deploy). Le
migration girano da sole a ogni avvio del container: se falliscono, il container
si ferma invece di servire uno schema incoerente, e l'errore è nei log di Coolify.

## Provare in locale

```bash
cp .env.example .env          # compila SECRET_KEY e POSTGRES_PASSWORD
docker compose up --build
# l'app risponde su http://localhost:8000
```

## Note

- **Lo schema è gestito da Alembic.** L'app non crea più tabelle all'avvio:
  quello era un espediente per il serverless, e su un database vuoto faceva
  fallire le migration.
- **SQLite**: se proprio vuoi usarlo al posto di Postgres, il file deve stare su
  un volume persistente (`DATABASE_URL=sqlite:////data/app.db` e un volume
  montato su `/data`), altrimenti i dati spariscono a ogni redeploy.
- **Worker**: due di default. Alzali con `WEB_CONCURRENCY` se serve.
