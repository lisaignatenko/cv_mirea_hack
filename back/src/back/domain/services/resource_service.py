from datetime import datetime, timezone
from uuid import uuid4

from back.data.repositories.resource_repository import ResourceRepository
from back.domain.models import Resource


class ResourceService:
    def __init__(self, repository: ResourceRepository) -> None:
        self._repository = repository

    async def create_resource(self, name: str, description: str | None) -> Resource:
        if len(name) == 0:
            raise ValueError("Resource name must not be empty")

        resource = Resource(id=uuid4(), name=name, description=description)
        await self._repository.add(resource)
        return resource

    async def list_resources(self) -> list[Resource]:
        return await self._repository.list_resources()

    async def touch_resource(self, resource_id: str) -> datetime:
        if len(resource_id) == 0:
            raise ValueError("Resource identifier must not be empty")

        touched_at = datetime.now(timezone.utc)
        await self._repository.update_last_accessed(resource_id, touched_at)
        return touched_at
