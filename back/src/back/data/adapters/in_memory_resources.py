from datetime import datetime
from uuid import UUID

from back.data.repositories import ResourceRepository
from back.domain.models import Resource


class InMemoryResourceRepository(ResourceRepository):
    def __init__(self) -> None:
        self._resources: dict[UUID, Resource] = {}
        self._access_log: dict[str, datetime] = {}

    async def add(self, resource: Resource) -> None:
        if resource.id in self._resources:
            raise ValueError("Resource already exists")
        self._resources[resource.id] = resource

    async def list_resources(self) -> list[Resource]:
        return list(self._resources.values())

    async def update_last_accessed(self, resource_id: str, timestamp: datetime) -> None:
        known_ids = {str(identifier) for identifier in self._resources}
        if resource_id not in known_ids:
            raise ValueError("Resource not found")
        self._access_log[resource_id] = timestamp
