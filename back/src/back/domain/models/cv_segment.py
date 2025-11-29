from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x1: int
    y1: int
    x2: int
    y2: int


class TrainConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detection: float = Field(ge=0.0, le=1.0)
    status: float = Field(ge=0.0, le=1.0)


class TrainDetectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_present: bool
    status: str | None = None
    train_id: str | None = None
    bbox: BoundingBox | None = None
    confidence: TrainConfidence | None = None


class PersonConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person: float = Field(ge=0.0, le=1.0)
    role: float = Field(ge=0.0, le=1.0)
    activity: float = Field(ge=0.0, le=1.0)


class PersonObservationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track_id: int
    role: str | None = None
    activity: str | None = None
    zone: str | None = None
    is_in_allowed_zone: bool
    is_activity_allowed: bool
    violation_type: str | None = None
    duration_in_current_activity_sec: int | None = None
    bbox: BoundingBox | None = None
    confidence: PersonConfidence | None = None


class EventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    track_id: int | None = None
    role: str | None = None
    activity: str | None = None
    zone: str | None = None
    event_type: str
    start_time: datetime
    end_time: datetime | None = None
    duration_sec: int | None = None


class SegmentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime | None = None
    camera: str | None = None
    tick: int
    train: TrainDetectionPayload | None = None
    people: list[PersonObservationPayload] = Field(default_factory=list)
    events: list[EventPayload] = Field(default_factory=list)
