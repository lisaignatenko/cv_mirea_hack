# Backend service

This FastAPI backend is intended to run inside Docker using the provided `compose.yml`. The
stack includes a Postgres service with persisted data, a one-shot migrations job, and the
application container.

## Environment

These variables are required by the backend and migrations service:

- `DATABASE_URL`: Postgres connection string (e.g. `postgresql://postgres:postgres@db:5432/postgres`).
- `MIGRATIONS_STATE_DIR`: Shared directory used for migration status tracking
  (mounted at `/var/run/migrations` by default).
- `FRONTEND_HEALTH_URL`: URL the backend polls to confirm the frontend is healthy.
- `CV_HEALTH_URL`: URL the backend polls to confirm the CV worker is healthy.

Create the virtual environment with `uv sync --frozen`; the resulting `.venv` directory is
ignored by Git so CI runners can recreate it without tripping over checked-in placeholders.

## Docker Compose services

- **db**: Postgres 16 with credentials defined via `POSTGRES_USER`, `POSTGRES_PASSWORD`, and
  `POSTGRES_DB`. Data persists through the `db_data` volume.
- **migrations**: Runs `python -m back.data.migrations` once to create the `alembic_version`
  table and seed an initial revision. It writes a lock file and `status.json` in
  `MIGRATIONS_STATE_DIR` to signal progress.
- **back**: Depends on the migrations job finishing successfully and the database health
  check. It polls the migration status files before continuing the startup lifespan.

## Migration status files

The shared directory contains:

- `migrations.lock`: Present while the migrations container is running.
- `status.json`: JSON payload describing the latest migration status and detail message.

If `status.json` reports `failed`, the backend will stop booting until migrations succeed.

## Running migrations manually

Migrations normally run automatically through Docker Compose. To rerun them manually:

```bash
docker compose run --rm migrations
```

Inspect the current migration status without starting the backend:

```bash
docker compose run --rm back ls /var/run/migrations
```
