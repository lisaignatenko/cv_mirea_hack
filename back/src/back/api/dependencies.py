from collections.abc import AsyncIterator

import httpx
from fastapi import Depends

from back.api.app import _require_env
from back.data.adapters import InMemoryResourceRepository
from back.domain.services import CVWorkflowService, FrontendInteractionService, ResourceService

_resource_repository = InMemoryResourceRepository()
_frontend_service = FrontendInteractionService()
_resource_service = ResourceService(_resource_repository)


async def get_frontend_service() -> FrontendInteractionService:
    return _frontend_service


def get_resource_service() -> ResourceService:
    return _resource_service


async def cv_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client


async def get_cv_workflow_service(
    client: httpx.AsyncClient = Depends(cv_client),
) -> CVWorkflowService:
    workflow_url = _require_env("CV_WORKFLOW_URL")
    return CVWorkflowService(workflow_url=workflow_url, client=client)
