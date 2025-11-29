from uuid import UUID

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoints(async_client: AsyncClient) -> None:
    ping_response = await async_client.get("/ping")
    assert ping_response.status_code == 200
    assert ping_response.json() == {"message": "pong"}

    health_response = await async_client.get("/health/ping")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_frontend_routes(async_client: AsyncClient) -> None:
    session_response = await async_client.post(
        "/frontend/sessions",
        json={"metadata": {"origin": "test-suite"}},
    )

    assert session_response.status_code == 200
    session_payload = session_response.json()
    session_id = UUID(session_payload["id"])
    assert session_payload["metadata"] == {"origin": "test-suite"}

    task_response = await async_client.post(
        "/frontend/tasks",
        json={"session_id": str(session_id), "payload": {"example": True}},
    )

    assert task_response.status_code == 200
    task_payload = task_response.json()
    assert UUID(task_payload["id"])
    assert UUID(task_payload["session_id"]) == session_id
    assert task_payload["payload"] == {"example": True}


@pytest.mark.asyncio
async def test_resource_routes(async_client: AsyncClient) -> None:
    create_response = await async_client.post(
        "/resources",
        json={"name": "example", "description": "resource"},
    )

    assert create_response.status_code == 200
    created_payload = create_response.json()
    resource_id = created_payload["id"]
    assert created_payload["name"] == "example"
    assert created_payload["description"] == "resource"

    list_response = await async_client.get("/resources")
    assert list_response.status_code == 200
    listed = list_response.json()["resources"]
    assert any(item["id"] == resource_id for item in listed)

    touch_response = await async_client.post(f"/resources/{resource_id}/touch")
    assert touch_response.status_code == 200
    touch_payload = touch_response.json()
    assert touch_payload["resource_id"] == resource_id
    assert isinstance(touch_payload["touched_at"], str)


@pytest.mark.asyncio
async def test_cv_workflow_route(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/cv/workflow",
        json={"payload": {"value": 42}},
    )

    assert response.status_code == 200
    assert response.json() == {"result": {"forwarded": {"value": 42}}}
