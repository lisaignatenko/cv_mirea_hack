from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, List

import cv2


@dataclass
class MotionBox:
    bbox: Tuple[int, int, int, int]
    area: int


class MotionDetector:
    def __init__(self, min_area: int = 1000, history: int = 500, var_threshold: float = 16.0):
        """Detect moving regions in static-camera video using background subtraction."""
        self.subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=True,
        )
        self.min_area = min_area

    def detect(self, frame) -> List[MotionBox]:
        """Return bounding boxes of moving regions for a frame."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fgmask = self.subtractor.apply(gray)
        _, fgmask = cv2.threshold(fgmask, 200, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel, iterations=1)
        fgmask = cv2.dilate(fgmask, kernel, iterations=2)
        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes: List[MotionBox] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            boxes.append(MotionBox(bbox=(x, y, x + w, y + h), area=int(area)))

        return boxes
