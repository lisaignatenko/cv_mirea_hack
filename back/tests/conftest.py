import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

import back.api.app as api_app
from back.api.dependencies import get_cv_workflow_service


class StubCVWorkflowService:
    async def forward_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"forwarded": payload}


@pytest.fixture
def test_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FastAPI:
    state_dir = tmp_path / "migrations_state"
    state_dir.mkdir()

    monkeypatch.setenv("FRONTEND_HEALTH_URL", "http://frontend/health")
    monkeypatch.setenv("CV_HEALTH_URL", "http://cv/health")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
    monkeypatch.setenv("MIGRATIONS_STATE_DIR", str(state_dir))

    async def _noop_wait(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(api_app, "_wait_for_http_health", _noop_wait)
    monkeypatch.setattr(api_app, "_wait_for_database", _noop_wait)
    monkeypatch.setattr(api_app, "_wait_for_migrations", _noop_wait)

    fastapi_app = api_app.app()
    stub_service = StubCVWorkflowService()

    async def get_stub_service() -> StubCVWorkflowService:
        return stub_service

    fastapi_app.dependency_overrides[get_cv_workflow_service] = get_stub_service
    return fastapi_app


@pytest_asyncio.fixture
async def async_client(test_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _sleep)


@pytest.fixture
def migrations_state_dir(tmp_path: Path) -> Path:
    state_dir = tmp_path / "migrations_state"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def fake_database_url() -> str:
    return "postgresql://user:pass@localhost:5432/test_db"
