import asyncio
import json
from pathlib import Path

import httpx
import pytest

from back.api import app as api_app


@pytest.mark.asyncio
async def test_wait_for_http_health_recovers(no_sleep: None) -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(status_code=500)
        return httpx.Response(status_code=200)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        await api_app._wait_for_http_health(client, "http://service.local/ping")

    assert attempts == 2


@pytest.mark.asyncio
async def test_wait_for_database_retries(
    no_sleep: None, monkeypatch: pytest.MonkeyPatch, fake_database_url: str
) -> None:
    attempts = 0

    async def fake_assertion(database_url: str) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise RuntimeError(f"Database {database_url} not ready")

    monkeypatch.setattr(api_app, "_assert_migrations_ready", fake_assertion)
    await api_app._wait_for_database(fake_database_url)

    assert attempts == 2


@pytest.mark.asyncio
async def test_wait_for_migrations_respects_lock(
    monkeypatch: pytest.MonkeyPatch, migrations_state_dir: Path
) -> None:
    status_path = migrations_state_dir / api_app.MIGRATIONS_STATUS_FILENAME
    lock_path = migrations_state_dir / api_app.MIGRATIONS_LOCK_FILENAME
    status_path.write_text(
        json.dumps({"status": "running", "detail": "in progress"}),
        encoding="utf-8",
    )
    lock_path.touch()

    async def unlock_after_wait(_: float) -> None:
        status_path.write_text(
            json.dumps({"status": "completed", "detail": "done"}),
            encoding="utf-8",
        )
        if lock_path.exists():
            lock_path.unlink()

    monkeypatch.setattr(asyncio, "sleep", unlock_after_wait)
    await api_app._wait_for_migrations(migrations_state_dir)


@pytest.mark.asyncio
async def test_wait_for_migrations_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state_dir = tmp_path / "migrations_failure_test"
    state_dir.mkdir(parents=True, exist_ok=True)

    status_path = state_dir / api_app.MIGRATIONS_STATUS_FILENAME
    status_path.write_text(
        json.dumps({"status": "failed", "detail": "boom"}),
        encoding="utf-8",
    )

    async def fast_wait(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fast_wait)
    with pytest.raises(RuntimeError, match="Migrations failed: boom"):
        await api_app._wait_for_migrations(state_dir)


def test_read_migration_state_requires_strings(migrations_state_dir: Path) -> None:
    status_path = migrations_state_dir / api_app.MIGRATIONS_STATUS_FILENAME
    status_path.write_text(json.dumps({"status": 1, "detail": 2}), encoding="utf-8")

    with pytest.raises(TypeError):
        api_app._read_migration_state(migrations_state_dir)
