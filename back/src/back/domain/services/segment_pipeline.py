import asyncio

import httpx

from back.data.repositories import SegmentRepository
from back.domain.models import SegmentPayload


class SegmentPipelineService:
    def __init__(
        self,
        *,
        segment_url: str,
        frontend_segment_url: str,
        repository: SegmentRepository,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        if len(segment_url) == 0:
            raise ValueError("CV segment URL must not be empty")
        if len(frontend_segment_url) == 0:
            raise ValueError("Frontend segment URL must not be empty")
        if poll_interval_seconds <= 0.0:
            raise ValueError("Poll interval must be positive")

        self._segment_url = segment_url
        self._frontend_segment_url = frontend_segment_url
        self._repository = repository
        self._poll_interval_seconds = poll_interval_seconds
        self._next_id = 0
        self._task: asyncio.Task[None] | None = None
        self._client = httpx.AsyncClient()

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def next_tick(self) -> int:
        return self._next_id

    async def start(self) -> None:
        if self.is_running:
            raise RuntimeError("Segment pipeline already running")
        await self._repository.reset()
        self._next_id = 0
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        while True:
            await self._process_tick()
            self._next_id += 1
            await asyncio.sleep(self._poll_interval_seconds)

    async def _process_tick(self) -> None:
        response = await self._client.post(self._segment_url, json={"id": self._next_id})
        response.raise_for_status()
        response_json = response.json()
        if not isinstance(response_json, dict):
            raise TypeError("CV segment response must be a JSON object")

        payload = SegmentPayload.model_validate(response_json)
        await self._repository.record_segment(payload)

        frontend_response = await self._client.post(
            self._frontend_segment_url, json=payload.model_dump(mode="json")
        )
        frontend_response.raise_for_status()

    async def aclose(self) -> None:
        await self._client.aclose()
