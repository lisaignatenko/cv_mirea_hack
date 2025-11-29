from abc import ABC, abstractmethod

from back.domain.models import SegmentPayload


class SegmentRepository(ABC):
    @abstractmethod
    async def reset(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def record_segment(self, payload: SegmentPayload) -> None:
        raise NotImplementedError
