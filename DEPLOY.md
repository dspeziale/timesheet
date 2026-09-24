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
   | `APP_NAME` | `Timesheet` (facoltativa) |
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

### Da un altro PostgreSQL (es. Neon)

Lo schema è identico, quindi basta un dump:

```bash
pg_dump "$VECCHIO_DATABASE_URL" --no-owner --no-acl -Fc -f timesheet.dump
pg_restore -d "$NUOVO_DATABASE_URL" --no-owner --no-acl timesheet.dump
```

Se invece punti il nuovo container al database Neon già esistente, non serve
fare nulla: `flask db upgrade` vede lo schema già aggiornato e non tocca niente.

## Se il deploy fallisce

All'avvio il container attende il database (30 tentativi ogni 2 secondi) prima
di applicare le migration. Se non lo raggiunge, esce con un messaggio che dice
quale sia il problema invece del traceback di SQLAlchemy:

| Messaggio nei log | Cosa controllare |
|---|---|
| `L'hostname del database non si risolve` | Il PostgreSQL è avviato? L'hostname in `DATABASE_URL` è quello **attuale**? Cancellando e ricreando il database in Coolify l'hostname cambia. |
| `Credenziali rifiutate` | La password è applicata solo alla prima creazione del volume, quindi quella mostrata nell'interfaccia può essere disallineata. Dal *Terminal* del database: `psql -U postgres -c "ALTER USER postgres PASSWORD '...';"` |
| `Il database indicato non esiste` | L'ultima parte di `DATABASE_URL`, dopo la porta. |
| `Connessione rifiutata` | L'host risponde ma non c'è PostgreSQL in ascolto su quella porta. |

L'attesa si regola con `DB_WAIT_ATTEMPTS` e `DB_WAIT_INTERVAL`.

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
- **PostgreSQL è obbligatorio.** Senza `DATABASE_URL` l'applicazione si
  rifiuta di partire, invece di ripiegare in silenzio su un database locale
  che verrebbe svuotato a ogni redeploy.
- **Worker**: due di default. Alzali con `WEB_CONCURRENCY` se serve.
