from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from back.api.dependencies import get_segment_pipeline_service
from back.domain.services import SegmentPipelineService

router = APIRouter(prefix="/segment", tags=["segment"])


class SegmentStatusResponse(BaseModel):
    is_running: bool
    next_tick: int

    @classmethod
    def from_service(cls, service: SegmentPipelineService) -> "SegmentStatusResponse":
        return cls(is_running=service.is_running, next_tick=service.next_tick)


@router.post("/start", response_model=SegmentStatusResponse)
async def start_segment_pipeline(
    service: SegmentPipelineService = Depends(get_segment_pipeline_service),
) -> SegmentStatusResponse:
    if service.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Segment pipeline already running"
        )
    await service.start()
    return SegmentStatusResponse.from_service(service)


@router.post("/stop", response_model=SegmentStatusResponse)
async def stop_segment_pipeline(
    service: SegmentPipelineService = Depends(get_segment_pipeline_service),
) -> SegmentStatusResponse:
    await service.stop()
    return SegmentStatusResponse.from_service(service)


@router.get("/status", response_model=SegmentStatusResponse)
async def segment_pipeline_status(
    service: SegmentPipelineService = Depends(get_segment_pipeline_service),
) -> SegmentStatusResponse:
    return SegmentStatusResponse.from_service(service)
