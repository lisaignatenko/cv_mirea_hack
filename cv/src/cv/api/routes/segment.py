from typing import Any

from fastapi import APIRouter

from cv.api.schemas import RequestPayload

router = APIRouter(tags=["segment"])


@router.post("/segment")
async def segment(payload: RequestPayload) -> dict[str, Any]:
    return ВАША_ФУНКЦИЯ(payload.id)
