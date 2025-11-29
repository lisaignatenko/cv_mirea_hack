import json
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from cv.api.schemas import RequestPayload
from detection.video_inference.video_processing_api import process_frame

router = APIRouter(tags=["segment"])


@router.post("/segment")
async def segment(payload: RequestPayload) -> dict[str, Any]:
    return await process_frame("repairs.mov", index = payload.id)
