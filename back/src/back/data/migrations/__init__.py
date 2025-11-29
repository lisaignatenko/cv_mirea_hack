"""Database migration entrypoints."""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg

MIGRATIONS_STATUS_FILENAME = "status.json"
MIGRATIONS_LOCK_FILENAME = "migrations.lock"
INITIAL_VERSION = "0001_initial"


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


def _apply_base_schema(database_url: str) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS alembic_version ("  # noqa: S608
                "version_num VARCHAR(32) PRIMARY KEY"
                ");",
            )
            connection.commit()

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
