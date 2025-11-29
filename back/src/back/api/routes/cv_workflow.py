from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from back.api.dependencies import get_cv_workflow_service
from back.domain.services import CVWorkflowService

router = APIRouter(prefix="/cv", tags=["cv"])


class CVWorkflowRequest(BaseModel):
    payload: dict[str, Any]


class CVWorkflowResponse(BaseModel):
    result: dict[str, Any]


@router.post("/workflow", response_model=CVWorkflowResponse)
async def forward_to_workflow(
    request: CVWorkflowRequest,
    service: CVWorkflowService = Depends(get_cv_workflow_service),
) -> CVWorkflowResponse:
    forwarded = await service.forward_payload(request.payload)
    return CVWorkflowResponse(result=forwarded)
