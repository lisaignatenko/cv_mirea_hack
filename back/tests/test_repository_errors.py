from datetime import datetime, timezone
from uuid import uuid4

import pytest

from back.data.adapters import InMemoryResourceRepository
from back.domain.models import Resource


@pytest.mark.asyncio
async def test_resource_repository_rejects_duplicates() -> None:
    repository = InMemoryResourceRepository()
    resource = Resource(id=uuid4(), name="alpha", description=None)

    await repository.add(resource)
    with pytest.raises(ValueError, match="Resource already exists"):
        await repository.add(resource)


@pytest.mark.asyncio
async def test_resource_repository_requires_known_id() -> None:
    repository = InMemoryResourceRepository()
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="Resource not found"):
        await repository.update_last_accessed("missing", timestamp)
