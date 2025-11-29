from typing import Any, Dict, Optional
import json

from fastapi import APIRouter

from cv.api.schemas import RequestPayload

router = APIRouter(tags=["segment"])


def get_jsonl_line(file_path, line_index) -> Optional[Dict]:
    with open(file_path, 'r', encoding='utf-8') as file:
        for current_line, line in enumerate(file):
            if current_line == line_index:
                return json.loads(line.strip())
    return None

@router.post("/segment")
async def segment(payload: RequestPayload) -> dict[str, Any]:
    # TODO figure out path to data.jsonl
    return get_jsonl_line('data.jsonl', payload.id)
