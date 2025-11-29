from pathlib import Path
from typing import Any

from fastapi import APIRouter

from cv.api.schemas import RequestPayload
from cv.detection.video_inference.video_processing_api import process_frame

router = APIRouter(tags=["segment"])

CURRENT_DIR = Path(__file__).resolve().parent
VIDEO_PATH = CURRENT_DIR / "repairs.mov"


@router.post("/segment")
async def segment(payload: RequestPayload) -> dict[str, Any]:
    return await process_frame(str(VIDEO_PATH), index=payload.id)
