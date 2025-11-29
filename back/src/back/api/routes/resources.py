from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from back.api.dependencies import get_resource_service
from back.domain.models import Resource
from back.domain.services import ResourceService

router = APIRouter(prefix="/resources", tags=["resources"])


class ResourceCreateRequest(BaseModel):
    name: str
    description: str | None = None


class ResourceResponse(BaseModel):
    id: UUID
    name: str
    description: str | None

    @classmethod
    def from_domain(cls, resource: Resource) -> "ResourceResponse":
        return cls(id=resource.id, name=resource.name, description=resource.description)


class ResourceListResponse(BaseModel):
    resources: list[ResourceResponse]


class ResourceTouchResponse(BaseModel):
    resource_id: str
    touched_at: datetime


@router.post("", response_model=ResourceResponse)
async def create_resource(
    request: ResourceCreateRequest,
    service: ResourceService = Depends(get_resource_service),
) -> ResourceResponse:
    resource = await service.create_resource(request.name, request.description)
    return ResourceResponse.from_domain(resource)


@router.get("", response_model=ResourceListResponse)
async def list_resources(
    service: ResourceService = Depends(get_resource_service),
) -> ResourceListResponse:
    resources = await service.list_resources()
    return ResourceListResponse(
        resources=[ResourceResponse.from_domain(resource) for resource in resources]
    )


@router.post("/{resource_id}/touch", response_model=ResourceTouchResponse)
async def touch_resource(
    resource_id: str,
    service: ResourceService = Depends(get_resource_service),
) -> ResourceTouchResponse:
    try:
        touched_at = await service.touch_resource(resource_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResourceTouchResponse(resource_id=resource_id, touched_at=touched_at)
