from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from back.api.dependencies import get_frontend_service, get_segment_pipeline_service
from back.domain.models import SegmentPayload, Session, Task
from back.domain.services import FrontendInteractionService, SegmentPipelineService

router = APIRouter(prefix="/frontend", tags=["frontend"])


class SessionStartRequest(BaseModel):
    metadata: dict[str, str] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    id: UUID
    created_at: str
    metadata: dict[str, str]

    @classmethod
    def from_domain(cls, session: Session) -> "SessionResponse":
        return cls(
            id=session.id,
            created_at=session.created_at.isoformat(),
            metadata=session.metadata,
        )


class TaskStartRequest(BaseModel):
    session_id: UUID
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    id: UUID
    session_id: UUID
    created_at: str
    payload: dict[str, Any]

    @classmethod
    def from_domain(cls, task: Task) -> "TaskResponse":
        return cls(
            id=task.id,
            session_id=task.session_id,
            created_at=task.created_at.isoformat(),
            payload=task.payload,
        )


@router.post("/sessions", response_model=SessionResponse)
async def start_session(
    request: SessionStartRequest,
    service: FrontendInteractionService = Depends(get_frontend_service),
) -> SessionResponse:
    session = await service.start_session(request.metadata)
    return SessionResponse.from_domain(session)


@router.post("/tasks", response_model=TaskResponse)
async def start_task(
    request: TaskStartRequest,
    service: FrontendInteractionService = Depends(get_frontend_service),
) -> TaskResponse:
    try:
        task = await service.start_task(request.session_id, request.payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return TaskResponse.from_domain(task)


@router.post("/segment", status_code=status.HTTP_204_NO_CONTENT)
async def forward_segment_payload(
    payload: SegmentPayload,
    service: SegmentPipelineService = Depends(get_segment_pipeline_service),
) -> None:
    await service.forward_to_frontend(payload)
