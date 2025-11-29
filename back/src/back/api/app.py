import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import psycopg
from fastapi import FastAPI

from back.api.routes.health import router as health_router

HTTP_TIMEOUT_SECONDS = 5.0
RETRY_DELAY_SECONDS = 1.0


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

    async with httpx.AsyncClient() as client:
        await asyncio.gather(
            _wait_for_http_health(client, frontend_url),
            _wait_for_http_health(client, cv_url),
            _wait_for_database(database_url),
        )

    yield


def app() -> FastAPI:
    fastapi_app = FastAPI(title="back service", lifespan=_lifespan)

    fastapi_app.include_router(health_router)

    return fastapi_app
