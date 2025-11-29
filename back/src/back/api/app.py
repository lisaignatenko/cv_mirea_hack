import asyncio
import copy
import json
import logging
import logging.config
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import psycopg
from fastapi import FastAPI

HTTP_TIMEOUT_SECONDS = 5.0
RETRY_DELAY_SECONDS = 1.0
MIGRATIONS_STATUS_FILENAME = "status.json"
MIGRATIONS_LOCK_FILENAME = "migrations.lock"


def _configure_logging() -> None:
    app_logger = logging.getLogger("back")
    if app_logger.handlers:
        return

    from uvicorn.config import LOGGING_CONFIG

    logging_config = copy.deepcopy(LOGGING_CONFIG)
    logging_config["loggers"]["back"] = {
        "handlers": ["default"],
        "level": "INFO",
        "propagate": False,
    }
    logging.config.dictConfig(logging_config)


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise RuntimeError(f"Environment variable {key} is required")
    if len(value) == 0:
        raise RuntimeError(f"Environment variable {key} must not be empty")
    return value


async def _wait_for_http_health(client: httpx.AsyncClient, url: str) -> None:
    while True:
        try:
            response = await client.get(url, timeout=HTTP_TIMEOUT_SECONDS)
            response.raise_for_status()
            return
        except Exception as exc:  # noqa: BLE001
            print(f"Healthcheck for {url} failed: {exc}")
            await asyncio.sleep(RETRY_DELAY_SECONDS)


def _read_migration_state(state_dir: Path) -> dict[str, str] | None:
    status_path = state_dir / MIGRATIONS_STATUS_FILENAME
    if not status_path.exists():
        return None

    content = status_path.read_text(encoding="utf-8")
    payload = json.loads(content)
    status = payload.get("status")
    detail = payload.get("detail")

    if not isinstance(status, str):
        raise TypeError("Migration status must be a string")
    if not isinstance(detail, str):
        raise TypeError("Migration detail must be a string")

    return {"status": status, "detail": detail}


async def _wait_for_migrations(state_dir: Path) -> None:
    while True:
        if not state_dir.exists():
            print("Waiting for migrations state directory to appear")
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            continue
        if not state_dir.is_dir():
            raise RuntimeError("MIGRATIONS_STATE_DIR must be a directory")

        lock_path = state_dir / MIGRATIONS_LOCK_FILENAME
        lock_exists = lock_path.exists()
        migration_state = _read_migration_state(state_dir)

        if migration_state is None:
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            continue

        status = migration_state["status"]
        detail = migration_state["detail"]

        if status == "failed":
            raise RuntimeError(f"Migrations failed: {detail}")
        if status == "completed" and not lock_exists:
            return

        await asyncio.sleep(RETRY_DELAY_SECONDS)


async def _assert_migrations_ready(database_url: str) -> None:
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT 1;")
            health_row = await cursor.fetchone()
            if health_row is None:
                raise RuntimeError("Database health check returned no result")
            if not isinstance(health_row[0], int):
                raise TypeError("Unexpected database health check result type")

            await cursor.execute(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'alembic_version'"
                ");",
            )
            table_row = await cursor.fetchone()
            if table_row is None:
                raise RuntimeError("Migration metadata query returned no result")
            migration_table_exists = table_row[0]
            if not isinstance(migration_table_exists, bool):
                raise TypeError("Migration metadata query returned non-boolean flag")
            if not migration_table_exists:
                raise RuntimeError("Migration table alembic_version not found")

            await cursor.execute("SELECT COUNT(*) FROM alembic_version;")
            version_row = await cursor.fetchone()
            if version_row is None:
                raise RuntimeError("Migration version query returned no result")
            migration_versions = version_row[0]
            if not isinstance(migration_versions, int):
                raise TypeError("Migration version query returned non-integer count")
            if migration_versions < 1:
                raise RuntimeError("No migration versions applied")

            await connection.commit()


async def _wait_for_database(database_url: str) -> None:
    while True:
        try:
            await _assert_migrations_ready(database_url)
            return
        except Exception as exc:  # noqa: BLE001
            print(f"Database not ready: {exc}")
            await asyncio.sleep(RETRY_DELAY_SECONDS)


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    frontend_url = _require_env("FRONTEND_HEALTH_URL")
    cv_url = _require_env("CV_HEALTH_URL")
    database_url = _require_env("DATABASE_URL")
    migrations_state_dir_env = _require_env("MIGRATIONS_STATE_DIR")
    migrations_state_dir = Path(migrations_state_dir_env)

    await _wait_for_migrations(migrations_state_dir)

    async with httpx.AsyncClient() as client:
        await asyncio.gather(
            _wait_for_http_health(client, frontend_url),
            _wait_for_http_health(client, cv_url),
            _wait_for_database(database_url),
        )

    yield


from back.api.routes.cv_workflow import router as cv_router  # noqa: E402
from back.api.routes.frontend import router as frontend_router  # noqa: E402
from back.api.routes.health import router as health_router  # noqa: E402
from back.api.routes.resources import router as resources_router  # noqa: E402
from back.api.routes.segment_pipeline import router as segment_router  # noqa: E402


def app() -> FastAPI:
    _configure_logging()
    fastapi_app = FastAPI(title="back service", lifespan=_lifespan)

    fastapi_app.include_router(health_router)
    fastapi_app.include_router(frontend_router)
    fastapi_app.include_router(cv_router)
    fastapi_app.include_router(resources_router)
    fastapi_app.include_router(segment_router)

    return fastapi_app
