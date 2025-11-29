from abc import ABC, abstractmethod
from datetime import datetime

from back.domain.models import Resource


class ResourceRepository(ABC):
    @abstractmethod
    async def add(self, resource: Resource) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_resources(self) -> list[Resource]:
        raise NotImplementedError

    @abstractmethod
    async def update_last_accessed(self, resource_id: str, timestamp: datetime) -> None:
        raise NotImplementedError
