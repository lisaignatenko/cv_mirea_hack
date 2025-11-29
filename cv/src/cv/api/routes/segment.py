import json
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from cv.api.schemas import RequestPayload
from detection.video_inference.video_processing_api import process_frame

router = APIRouter(tags=["segment"])


def get_jsonl_line(file_path: str, line_index: int) -> Optional[Dict[str, Any]]:
    with open(file_path, "r", encoding="utf-8") as file:
        for current_line, line in enumerate(file):
            if current_line == line_index:
                return json.loads(line.strip())
    return None


@router.post("/segment")
async def segment(payload: RequestPayload) -> dict[str, Any]:
    return await process_frame("repairs.mov", index = payload.id)
