"""Database migration entrypoints."""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg

MIGRATIONS_STATUS_FILENAME = "status.json"
MIGRATIONS_LOCK_FILENAME = "migrations.lock"
INITIAL_VERSION = "0001_initial"
TABLE_NAMES = [
    "cv_events",
    "person_observations",
    "train_detections",
    "cv_frames",
]


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise RuntimeError(f"Environment variable {key} is required for migrations")
    if len(value) == 0:
        raise RuntimeError(f"Environment variable {key} must not be empty")
    return value


def _ensure_state_dir(state_dir: Path) -> None:
    if state_dir.exists() and not state_dir.is_dir():
        raise RuntimeError("MIGRATIONS_STATE_DIR must reference a directory")
    state_dir.mkdir(parents=True, exist_ok=True)


def _write_status(state_path: Path, status: str, detail: str) -> None:
    payload = {"status": status, "detail": detail}
    state_path.write_text(json.dumps(payload), encoding="utf-8")


def _drop_existing_tables(cursor: psycopg.Cursor[tuple[object, ...]]) -> None:
    for table_name in TABLE_NAMES:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")


def _apply_base_schema(database_url: str) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            _drop_existing_tables(cursor)
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS alembic_version ("  # noqa: S608
                "version_num VARCHAR(32) PRIMARY KEY"
                ");",
            )
            cursor.execute(
                "CREATE TABLE cv_frames ("  # noqa: S608
                "id BIGSERIAL PRIMARY KEY,"
                "ts TIMESTAMPTZ DEFAULT now(),"
                "tick INTEGER NOT NULL,"
                "camera TEXT NULL,"  # noqa: S105
                "CONSTRAINT uq_cv_frames_tick UNIQUE (tick)"
                ");",
            )
            cursor.execute(
                "CREATE INDEX idx_cv_frames_ts ON cv_frames (ts DESC);",  # noqa: S608
            )
            cursor.execute(
                "CREATE TABLE train_detections ("  # noqa: S608
                "id BIGSERIAL PRIMARY KEY,"
                "frame_id BIGINT NOT NULL REFERENCES cv_frames(id) ON DELETE CASCADE,"
                "is_present BOOLEAN NOT NULL,"
                "status TEXT NULL,"
                "train_id TEXT NULL,"
                "bbox_x1 INTEGER NULL,"
                "bbox_y1 INTEGER NULL,"
                "bbox_x2 INTEGER NULL,"
                "bbox_y2 INTEGER NULL,"
                "conf_detection REAL NULL,"
                "conf_status REAL NULL,"
                "CONSTRAINT uq_train_frame UNIQUE (frame_id)"
                ");",
            )
            cursor.execute(
                "CREATE INDEX idx_train_detections_frame ON train_detections (frame_id);",  # noqa: S608
            )
            cursor.execute(
                "CREATE TABLE person_observations ("  # noqa: S608
                "id BIGSERIAL PRIMARY KEY,"
                "frame_id BIGINT NOT NULL REFERENCES cv_frames(id) ON DELETE CASCADE,"
                "track_id INTEGER NOT NULL,"
                "role TEXT NULL,"
                "activity TEXT NULL,"
                "zone TEXT NULL,"
                "is_in_allowed_zone BOOLEAN NOT NULL,"
                "is_activity_allowed BOOLEAN NOT NULL,"
                "violation_type TEXT NULL,"
                "duration_in_current_activity_sec INTEGER NULL,"
                "bbox_x1 INTEGER NULL,"
                "bbox_y1 INTEGER NULL,"
                "bbox_x2 INTEGER NULL,"
                "bbox_y2 INTEGER NULL,"
                "conf_person REAL NULL,"
                "conf_role REAL NULL,"
                "conf_activity REAL NULL"
                ");",
            )
            cursor.execute(
                "CREATE INDEX idx_person_obs_frame ON person_observations (frame_id);",  # noqa: S608
            )
            cursor.execute(
                "CREATE INDEX idx_person_obs_track ON person_observations (track_id);",  # noqa: S608
            )
            cursor.execute(
                "CREATE INDEX idx_person_obs_role_activity ON person_observations (role, activity);",  # noqa: S608,E501
            )
            cursor.execute(
                "CREATE INDEX idx_person_obs_zone ON person_observations (zone);",  # noqa: S608
            )
            cursor.execute(
                "CREATE TABLE cv_events ("  # noqa: S608
                "id BIGSERIAL PRIMARY KEY,"
                "event_id TEXT NOT NULL,"
                "track_id INTEGER NULL,"
                "role TEXT NULL,"
                "activity TEXT NULL,"
                "zone TEXT NULL,"
                "event_type TEXT NOT NULL,"
                "start_time TIMESTAMPTZ NOT NULL,"
                "end_time TIMESTAMPTZ NULL,"
                "duration_sec INTEGER NULL,"
                "last_seen_frame_id BIGINT NULL REFERENCES cv_frames(id),"
                "CONSTRAINT uq_cv_events_event_id UNIQUE (event_id)"
                ");",
            )
            cursor.execute(
                "CREATE INDEX idx_cv_events_start ON cv_events (start_time DESC);",  # noqa: S608
            )
            cursor.execute(
                "CREATE INDEX idx_cv_events_track ON cv_events (track_id);",  # noqa: S608
            )
            cursor.execute(
                "CREATE INDEX idx_cv_events_event_type ON cv_events (event_type);",  # noqa: S608
            )
            cursor.execute("SELECT COUNT(*) FROM alembic_version;")
            count_row = cursor.fetchone()
            if count_row is None:
                raise RuntimeError("Migration version query returned no result")
            version_count = count_row[0]
            if not isinstance(version_count, int):
                raise TypeError("Migration version query returned non-integer count")

            if version_count == 0:
                cursor.execute(
                    "INSERT INTO alembic_version (version_num) VALUES (%s);",
                    (INITIAL_VERSION,),
                )
            else:
                cursor.execute("UPDATE alembic_version SET version_num = %s;", (INITIAL_VERSION,))
            connection.commit()


def run_migrations() -> None:
    database_url = _require_env("DATABASE_URL")
    state_dir_env = _require_env("MIGRATIONS_STATE_DIR")
    state_dir = Path(state_dir_env)

    _ensure_state_dir(state_dir)
    lock_path = state_dir / MIGRATIONS_LOCK_FILENAME
    state_path = state_dir / MIGRATIONS_STATUS_FILENAME

    lock_path.touch(exist_ok=True)
    _write_status(state_path, "running", "Applying database migrations")

    try:
        _apply_base_schema(database_url)
        _write_status(state_path, "completed", "Migrations applied successfully")
    except Exception as exc:  # noqa: BLE001
        _write_status(state_path, "failed", f"Migrations failed: {exc}")
        raise
    finally:
        if lock_path.exists():
            lock_path.unlink()
