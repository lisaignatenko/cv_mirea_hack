from datetime import datetime

import psycopg

from back.data.repositories import SegmentRepository
from back.domain.models import EventPayload, PersonObservationPayload, SegmentPayload


class PostgresSegmentRepository(SegmentRepository):
    def __init__(self, database_url: str) -> None:
        if len(database_url) == 0:
            raise ValueError("Database URL must not be empty")
        self._database_url = database_url

    async def reset(self) -> None:
        async with await psycopg.AsyncConnection.connect(self._database_url) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "TRUNCATE TABLE cv_events, person_observations, train_detections, cv_frames "
                    "RESTART IDENTITY CASCADE;"
                )
            await connection.commit()

    async def record_segment(self, payload: SegmentPayload) -> None:
        async with await psycopg.AsyncConnection.connect(self._database_url) as connection:
            async with connection.cursor() as cursor:
                frame_id = await self._store_frame(cursor, payload)
                await self._store_train(cursor, frame_id, payload)
                await self._store_people(cursor, frame_id, payload.people)
                await self._store_events(cursor, frame_id, payload.events)
            await connection.commit()

    async def _store_frame(
        self, cursor: psycopg.AsyncCursor[tuple[object, ...]], payload: SegmentPayload
    ) -> int:
        await cursor.execute(
            "INSERT INTO cv_frames (ts, tick, camera) VALUES (%s, %s, %s) "
            "ON CONFLICT (tick) DO UPDATE SET ts = EXCLUDED.ts, camera = EXCLUDED.camera "
            "RETURNING id;",
            (payload.timestamp, payload.tick, payload.camera),
        )
        frame_row = await cursor.fetchone()
        if frame_row is None:
            raise RuntimeError("Failed to persist cv frame")
        frame_id = frame_row[0]
        if not isinstance(frame_id, int):
            raise TypeError("Frame identifier must be integer")
        return frame_id

    async def _store_train(
        self,
        cursor: psycopg.AsyncCursor[tuple[object, ...]],
        frame_id: int,
        payload: SegmentPayload,
    ) -> None:
        if payload.train is None:
            return
        bbox = payload.train.bbox
        confidence = payload.train.confidence
        await cursor.execute(
            "INSERT INTO train_detections ("  # noqa: S608
            "frame_id, is_present, status, train_id, bbox_x1, bbox_y1, bbox_x2, bbox_y2, "
            "conf_detection, conf_status"  # noqa: E501
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (frame_id) DO UPDATE SET "
            "is_present = EXCLUDED.is_present, "
            "status = EXCLUDED.status, "
            "train_id = EXCLUDED.train_id, "
            "bbox_x1 = EXCLUDED.bbox_x1, "
            "bbox_y1 = EXCLUDED.bbox_y1, "
            "bbox_x2 = EXCLUDED.bbox_x2, "
            "bbox_y2 = EXCLUDED.bbox_y2, "
            "conf_detection = EXCLUDED.conf_detection, "
            "conf_status = EXCLUDED.conf_status;",
            (
                frame_id,
                payload.train.is_present,
                payload.train.status,
                payload.train.train_id,
                bbox.x1 if bbox else None,
                bbox.y1 if bbox else None,
                bbox.x2 if bbox else None,
                bbox.y2 if bbox else None,
                confidence.detection if confidence else None,
                confidence.status if confidence else None,
            ),
        )

    async def _store_people(
        self,
        cursor: psycopg.AsyncCursor[tuple[object, ...]],
        frame_id: int,
        people: list[PersonObservationPayload],
    ) -> None:
        for person in people:
            bbox = person.bbox
            confidence = person.confidence
            await cursor.execute(
                "INSERT INTO person_observations ("  # noqa: S608
                "frame_id, track_id, role, activity, zone, is_in_allowed_zone, "
                "is_activity_allowed, violation_type, duration_in_current_activity_sec, "
                "bbox_x1, bbox_y1, bbox_x2, bbox_y2, conf_person, conf_role, conf_activity"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
                (
                    frame_id,
                    person.track_id,
                    person.role,
                    person.activity,
                    person.zone,
                    person.is_in_allowed_zone,
                    person.is_activity_allowed,
                    person.violation_type,
                    person.duration_in_current_activity_sec,
                    bbox.x1 if bbox else None,
                    bbox.y1 if bbox else None,
                    bbox.x2 if bbox else None,
                    bbox.y2 if bbox else None,
                    confidence.person if confidence else None,
                    confidence.role if confidence else None,
                    confidence.activity if confidence else None,
                ),
            )

    async def _store_events(
        self,
        cursor: psycopg.AsyncCursor[tuple[object, ...]],
        frame_id: int,
        events: list[EventPayload],
    ) -> None:
        for event in events:
            await cursor.execute(
                "INSERT INTO cv_events ("  # noqa: S608
                "event_id, track_id, role, activity, zone, event_type, start_time, "
                "end_time, duration_sec, last_seen_frame_id"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (event_id) DO UPDATE SET "
                "track_id = EXCLUDED.track_id, "
                "role = EXCLUDED.role, "
                "activity = EXCLUDED.activity, "
                "zone = EXCLUDED.zone, "
                "event_type = EXCLUDED.event_type, "
                "start_time = LEAST(cv_events.start_time, EXCLUDED.start_time), "
                "end_time = EXCLUDED.end_time, "
                "duration_sec = EXCLUDED.duration_sec, "
                "last_seen_frame_id = EXCLUDED.last_seen_frame_id;",
                (
                    event.event_id,
                    event.track_id,
                    event.role,
                    event.activity,
                    event.zone,
                    event.event_type,
                    _ensure_datetime(event.start_time),
                    _ensure_optional_datetime(event.end_time),
                    event.duration_sec,
                    frame_id,
                ),
            )


def _ensure_datetime(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("Expected datetime instance")
    return value


def _ensure_optional_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise TypeError("Expected datetime instance")
    return value
