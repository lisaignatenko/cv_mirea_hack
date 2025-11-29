from __future__ import annotations

from pathlib import Path
from typing import Any
import asyncio

import cv2
import json
import numpy as np
from datetime import datetime, timedelta

from detection.detector import FactoryDetector, Detection
from .video import build_frame_json
from .ocr import TimestampOCR
from .motion import MotionDetector, MotionBox


_DETECTOR: FactoryDetector | None = None

def get_detector(device: str = "cuda") -> FactoryDetector:
    global _DETECTOR
    if _DETECTOR is None:
        _DETECTOR = FactoryDetector(
            device=device,
            target_labels=("person", "train"),
            tracking_enabled=True,
        )
    return _DETECTOR


def process_frame_sync(
    input_path: str,
    frame_index: int,
    device: str = "cuda",
    frame_stride: int = 3,
    camera_id: str = "camera_1",
) -> dict[str, Any]:
    video_path = Path(input_path)
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    raw_fps = cap.get(cv2.CAP_PROP_FPS)
    if not raw_fps or raw_fps <= 1e-2:
        raw_fps = 25.0
    effective_fps = raw_fps / max(frame_stride, 1)

    # Берём (или создаём) детектор
    detector = get_detector(device=device)
    detector.set_fps(effective_fps)

    ocr = TimestampOCR()
    motion_detector = MotionDetector(min_area=2000)

    # Перематываем на нужный кадр
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise IndexError(f"Frame index {frame_index} is out of range")

    # --- OCR по одному кадру ---
    ocr_res = ocr.recognize(frame)
    if ocr_res.timestamp is not None:
        timestamp_iso = ocr_res.timestamp.isoformat().replace("+00:00", "Z")
    else:
        # Для одиночного кадра без истории просто None
        timestamp_iso = None

    # --- motion + detection + safety ---
    motion_boxes = motion_detector.detect(frame)
    if motion_boxes:
        mb_simple = [mb.bbox for mb in motion_boxes]
        detections = detector.detect(frame, motion_boxes=mb_simple)
        safety_warnings = detector.check_safety_distances(detections)
    else:
        detections = []
        safety_warnings = []
    print(timestamp_iso)
    # --- тот самый json ---
    frame_json = build_frame_json(
        timestamp_iso=timestamp_iso,
        camera_id=camera_id,
        tick=frame_index,
        detections=detections,
        safety_warnings=safety_warnings,
        detector=detector,
    )
    return frame_json


async def process_frame(
    input_path: str,
    index: int,
    device: str = "cpu",
    frame_stride: int = 30,
    camera_id: str = "camera_1",
) -> dict[str, Any]:
    """
    Асинхронная обёртка над process_frame_sync.
    Можно дергать из любого async-кода.
    """
    return await asyncio.to_thread(
        process_frame_sync,
        input_path,
        index * frame_stride,
        device,
        frame_stride,
        camera_id,
    )
