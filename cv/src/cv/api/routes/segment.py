from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["segment"])

MOCK_SEGMENT_RESPONSE: dict[str, Any] = {
    "timestamp": "2025-11-29T08:15:23Z",
    "camera": "camera_1",
    "tick": 0,
    "train": {
        "is_present": True,
        "status": "standing",
        "train_id": "train_1",
        "bbox": {"x1": 0, "y1": 220, "x2": 1280, "y2": 720},
        "confidence": {"detection": 0.98, "status": 0.9},
    },
    "people": [
        {
            "track_id": 12,
            "role": "cleaner",
            "activity": "cleaning",
            "zone": "platform_floor",
            "is_in_allowed_zone": True,
            "is_activity_allowed": True,
            "violation_type": None,
            "duration_in_current_activity_sec": 37,
            "bbox": {"x1": 234, "y1": 120, "x2": 310, "y2": 260},
            "confidence": {"person": 0.97, "role": 0.92, "activity": 0.88},
        }
    ],
    "events": [
        {
            "event_id": "evt_0001",
            "track_id": 12,
            "role": "cleaner",
            "activity": "cleaning",
            "zone": "platform_floor",
            "event_type": "started",
            "start_time": "2025-11-29T08:14:46Z",
            "end_time": None,
            "duration_sec": None,
        }
    ],
}


@router.post("/segment")
async def segment() -> dict[str, Any]:
    return MOCK_SEGMENT_RESPONSE
