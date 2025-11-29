from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import json
import numpy as np
from datetime import datetime, timedelta

from detection.detector import FactoryDetector, Detection
from .ocr import TimestampOCR
from .motion import MotionDetector, MotionBox


def build_frame_json(
    timestamp_iso: str | None,
    camera_id: str,
    tick: int,
    detections: list[Detection],
    safety_warnings: list[tuple[Detection, Any, float]],
    detector: FactoryDetector,
) -> dict[str, Any]:
    """Build JSON structure for a single processed frame."""
    train_dets = [d for d in detections if d.label == "train"]
    if train_dets:
        train_det = max(
            train_dets,
            key=lambda d: (d.bbox[2] - d.bbox[0]) * (d.bbox[3] - d.bbox[1]),
        )
        x1, y1, x2, y2 = train_det.bbox
        train_part: dict[str, Any] = {
            "is_present": True,
            "status": "standing",
            "train_id": "train_1",
            "bbox": {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
            },
            "confidence": {
                "detection": float(train_det.score),
                "status": 0.5,
            },
        }
    else:
        train_part = {
            "is_present": False,
            "status": "absent",
            "train_id": None,
            "bbox": None,
            "confidence": {
                "detection": 0.0,
                "status": 0.0,
            },
        }

    people: list[dict[str, Any]] = []
    for det in detections:
        if det.label != "person":
            continue
        x1, y1, x2, y2 = det.bbox
        is_in_danger = any(w[0] is det for w in safety_warnings)
        person_json: dict[str, Any] = {
            "track_id": det.track_id,
            "role": None,
            "activity": None,
            "zone": None,
            "is_in_allowed_zone": (
                not is_in_danger if det.track_id is not None else None
            ),
            "is_activity_allowed": None,
            "violation_type": "danger_zone" if is_in_danger else None,
            "duration_in_current_activity_sec": None,
            "bbox": {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
            },
            "confidence": {
                "person": float(det.score),
                "role": None,
                "activity": None,
            },
        }
        people.append(person_json)

    events: list[dict[str, Any]] = []

    frame_json: dict[str, Any] = {
        "timestamp": timestamp_iso,
        "camera": camera_id,
        "tick": tick,
        "train": train_part,
        "people": people,
        "events": events,
    }
    return frame_json


def run_video(
    input_path: str,
    output_path: str | None = None,
    frame_stride: int = 3,
    show: bool = False,
    device: str = "cuda",
    save_metrics: bool = True,
    tracking: bool = True,
    jsonl_path: str = "frames.jsonl",
) -> None:
    """Run video processing pipeline: OCR, motion-gated detection, safety analysis, JSON export."""
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {input_path}")

    detector = FactoryDetector(
        device=device,
        target_labels=("person", "train"),
        tracking_enabled=tracking,
    )

    raw_fps = cap.get(cv2.CAP_PROP_FPS)
    if not raw_fps or raw_fps <= 1e-2:
        raw_fps = 25.0
    effective_fps = raw_fps / max(frame_stride, 1)
    detector.set_fps(effective_fps)

    ocr = TimestampOCR()
    motion_detector = MotionDetector(min_area=2000)

    frame_idx = 0
    detections: list[Detection] = []
    safety_warnings: list[tuple[Detection, object, float]] = []
    motion_boxes: list[MotionBox] = []
    writer: cv2.VideoWriter | None = None
    output_path_obj = Path(output_path) if output_path is not None else None

    jsonl_file = open(jsonl_path, "w", encoding="utf-8")
    track_colors: dict[int, tuple[int, int, int]] = {}
    last_timestamp: datetime | None = None
    last_timestamp_frame: int | None = None

    try:
        print(
            f"Raw FPS входного видео: {raw_fps}, "
            f"frame_stride={frame_stride}, "
            f"effective_fps={effective_fps}"
        )

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if writer is None and output_path_obj is not None:
                output_path_obj.parent.mkdir(parents=True, exist_ok=True)
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                h, w = frame.shape[:2]
                writer = cv2.VideoWriter(
                    str(output_path_obj),
                    fourcc,
                    max(effective_fps, 1.0),
                    (w, h),
                )
                if not writer.isOpened():
                    raise RuntimeError("Failed to open VideoWriter")

            if frame_idx % frame_stride == 0:
                res = ocr.recognize(frame)
                frame_dt = res.timestamp

                if frame_dt is not None:
                    last_timestamp = frame_dt
                    last_timestamp_frame = frame_idx
                    timestamp_iso = frame_dt.isoformat().replace("+00:00", "Z")
                else:
                    if (
                        last_timestamp is not None
                        and last_timestamp_frame is not None
                        and raw_fps > 0
                    ):
                        delta_frames = frame_idx - last_timestamp_frame
                        delta_seconds = delta_frames / raw_fps
                        approx_ts = last_timestamp + timedelta(seconds=delta_seconds)
                        timestamp_iso = approx_ts.isoformat().replace("+00:00", "Z")
                    else:
                        timestamp_iso = None

                motion_boxes = motion_detector.detect(frame)

                if motion_boxes:
                    mb_simple = [mb.bbox for mb in motion_boxes]
                    detections = detector.detect(frame, motion_boxes=mb_simple)
                    safety_warnings = detector.check_safety_distances(detections)
                else:
                    detections = []
                    safety_warnings = []

                frame_json = build_frame_json(
                    timestamp_iso=timestamp_iso,
                    camera_id="camera_1",
                    tick=frame_idx,
                    detections=detections,
                    safety_warnings=safety_warnings,
                    detector=detector,
                )
                jsonl_file.write(json.dumps(frame_json, ensure_ascii=False) + "\n")

            detector.draw_danger_zones(frame)

            for det in detections:
                x1, y1, x2, y2 = det.bbox
                is_in_danger = any(warning[0] is det for warning in safety_warnings)

                if det.label == "person":
                    if det.track_id is not None:
                        if det.track_id not in track_colors:
                            track_colors[det.track_id] = (
                                int(np.random.randint(0, 255)),
                                int(np.random.randint(0, 255)),
                                int(np.random.randint(0, 255)),
                            )
                        color = track_colors[det.track_id]
                    else:
                        color = (0, 255, 0)
                    if is_in_danger:
                        color = (0, 0, 255)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                    if det.track_id is not None:
                        text = f"ID:{det.track_id} {det.score:.2f}"
                    else:
                        text = f"Person {det.score:.2f}"

                    cv2.putText(
                        frame,
                        text,
                        (x1, max(y1 - 5, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        1,
                    )

                    foot_point = detector.get_person_foot_point(det.bbox)
                    cv2.circle(frame, foot_point, 5, (255, 255, 0), -1)

                    if (
                        detector.tracking_enabled
                        and detector.tracker
                        and det.track_id is not None
                    ):
                        metrics = detector.tracker.tracks.get(det.track_id)
                        if metrics and metrics.dominant_color:
                            color_rect_size = 20
                            color_x = x2 + 5
                            color_y = y1
                            cv2.rectangle(
                                frame,
                                (color_x, color_y),
                                (
                                    color_x + color_rect_size,
                                    color_y + color_rect_size,
                                ),
                                metrics.dominant_color,
                                -1,
                            )
                else:
                    color = (255, 0, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    text = f"{det.label} {det.score:.2f}"
                    cv2.putText(
                        frame,
                        text,
                        (x1, max(y1 - 5, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        1,
                    )

            for mb in motion_boxes:
                mx1, my1, mx2, my2 = mb.bbox
                cv2.rectangle(frame, (mx1, my1), (mx2, my2), (0, 165, 255), 1)

            for detection, zone, distance in safety_warnings:
                x1, y1, x2, y2 = detection.bbox
                warning_text = f"DANGER: {distance:.1f}px"
                cv2.putText(
                    frame,
                    warning_text,
                    (x1, max(y1 - 25, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 255),
                    2,
                )

            if writer is not None:
                writer.write(frame)

            if show:
                cv2.imshow("Safety Monitoring with Tracking", frame)
                key = cv2.waitKey(1)
                if key == 27:
                    break
                elif key == ord("p"):
                    cv2.waitKey(0)

            frame_idx += 1

    finally:
        if save_metrics:
            final_metrics = detector.get_metrics_summary()
            metrics_filename = (
                f"safety_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(metrics_filename, "w", encoding="utf-8") as f:
                json.dump(final_metrics, f, indent=2, ensure_ascii=False)
        jsonl_file.close()
        cap.release()
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()
