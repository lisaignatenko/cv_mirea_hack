from typing import Any

from httpx import AsyncClient


class CVWorkflowService:
    def __init__(self, workflow_url: str, client: AsyncClient) -> None:
        if len(workflow_url) == 0:
            raise ValueError("Workflow URL must not be empty")
        self._workflow_url = workflow_url
        self._client = client

    async def forward_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(self._workflow_url, json=payload)
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, dict):
            raise TypeError("CV workflow response must be a JSON object")
        return data
