from collections.abc import AsyncIterator

import httpx
from fastapi import Depends

from back.api.app import _require_env
from back.data.adapters import InMemoryResourceRepository, PostgresSegmentRepository
from back.domain.services import (
    CVWorkflowService,
    FrontendInteractionService,
    ResourceService,
    SegmentPipelineService,
)

_resource_repository = InMemoryResourceRepository()
_frontend_service = FrontendInteractionService()
_resource_service = ResourceService(_resource_repository)
_segment_service: SegmentPipelineService | None = None


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


async def get_segment_pipeline_service() -> SegmentPipelineService:
    global _segment_service
    if _segment_service is not None:
        return _segment_service

    database_url = _require_env("DATABASE_URL")
    segment_url = _require_env("CV_SEGMENT_URL")
    frontend_segment_url = _require_env("FRONTEND_SEGMENT_URL")
    repository = PostgresSegmentRepository(database_url)
    _segment_service = SegmentPipelineService(
        segment_url=segment_url,
        frontend_segment_url=frontend_segment_url,
        repository=repository,
    )
    return _segment_service
