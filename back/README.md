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

## Example `curl` workflow

The backend exposes inbound control endpoints and makes outbound calls to the CV worker and the
frontend segment endpoint.

### Inbound (calls to the backend)

Assuming the backend is reachable at `http://localhost:8001`:

```bash
# Start the pipeline (returns 409 if already running)
curl -X POST http://localhost:8001/segment/start

# Check current status
curl http://localhost:8001/segment/status

# Stop the pipeline
curl -X POST http://localhost:8001/segment/stop
```

### Outbound (calls made by the backend)

On each tick the backend posts to the CV worker and then forwards the validated payload to the
frontend. Example for tick `0`:

```bash
# Backend -> CV worker
curl -X POST http://cv:8000/segment \
  -H 'Content-Type: application/json' \
  -d '{
    "id": 0
  }'

# Sample CV response (validated and stored)
{
  "timestamp": "2025-11-29T08:15:23Z",
  "camera": "camera_1",
  "tick": 0,
  "train": {
    "is_present": true,
    "status": "standing",
    "train_id": "train_1",
    "bbox": {"x1": 0, "y1": 220, "x2": 1280, "y2": 720},
    "confidence": {"detection": 0.98, "status": 0.9}
  },
  "people": [
    {
      "track_id": 12,
      "role": "cleaner",
      "activity": "cleaning",
      "zone": "platform_floor",
      "is_in_allowed_zone": true,
      "is_activity_allowed": true,
      "violation_type": null,
      "duration_in_current_activity_sec": 37,
      "bbox": {"x1": 234, "y1": 120, "x2": 310, "y2": 260},
      "confidence": {"person": 0.97, "role": 0.92, "activity": 0.88}
    }
  ],
  "events": [
    {
      "event_id": "evt_0001",
      "track_id": 12,
      "role": "cleaner",
      "activity": "cleaning",
      "zone": "platform_floor",
      "event_type": "started",
      "start_time": "2025-11-29T08:14:46Z",
      "end_time": null,
      "duration_sec": null
    }
  ]
}

# Backend -> frontend forwarding (same payload forwarded to configured frontend URL)
curl -X POST http://frontend:3000/segment \
  -H 'Content-Type: application/json' \
  -d '{
    "timestamp": "2025-11-29T08:15:23Z",
    "camera": "camera_1",
    "tick": 0,
    "train": {
      "is_present": true,
      "status": "standing",
      "train_id": "train_1",
      "bbox": {"x1": 0, "y1": 220, "x2": 1280, "y2": 720},
      "confidence": {"detection": 0.98, "status": 0.9}
    },
    "people": [
      {
        "track_id": 12,
        "role": "cleaner",
        "activity": "cleaning",
        "zone": "platform_floor",
        "is_in_allowed_zone": true,
        "is_activity_allowed": true,
        "violation_type": null,
        "duration_in_current_activity_sec": 37,
        "bbox": {"x1": 234, "y1": 120, "x2": 310, "y2": 260},
        "confidence": {"person": 0.97, "role": 0.92, "activity": 0.88}
      }
    ],
    "events": [
      {
        "event_id": "evt_0001",
        "track_id": 12,
        "role": "cleaner",
        "activity": "cleaning",
        "zone": "platform_floor",
        "event_type": "started",
        "start_time": "2025-11-29T08:14:46Z",
        "end_time": null,
        "duration_sec": null
      }
    ]
  }'
```
