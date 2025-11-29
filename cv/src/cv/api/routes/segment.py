import json
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from cv.api.schemas import RequestPayload

# Directory of this file: cv_mirea_hack/cv/src/cv/api/routes
current_dir = os.path.dirname(__file__)

# Cringe
# (routes -> api -> cv -> src -> cv -> cv_mirea_hack) = 5 levels up
JSONL_FILE_PATH = os.path.abspath(os.path.join(current_dir, "frames.jsonl"))

router = APIRouter(tags=["segment"])


def get_jsonl_line(file_path: str, line_index: int) -> Optional[Dict[str, Any]]:
    with open(file_path, "r", encoding="utf-8") as file:
        for current_line, line in enumerate(file):
            if current_line == line_index:
                return json.loads(line.strip())
    return None


@router.post("/segment")
async def segment(payload: RequestPayload) -> dict[str, Any]:
    # Check that the file exists
    if not os.path.isfile(JSONL_FILE_PATH):
        raise HTTPException(
            status_code=500,
            detail=f"frames.jsonl not found at '{JSONL_FILE_PATH}'",
        )

    # Read the requested line
    data = get_jsonl_line(JSONL_FILE_PATH, payload.id)

    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No line with index {payload.id} in frames.jsonl",
        )

    return data
