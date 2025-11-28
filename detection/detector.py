from dataclasses import dataclass
from typing import List, Tuple, Sequence

import numpy as np
from ultralytics import YOLO


@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]
    score: float
    class_id: int
    label: str


class FactoryDetector:
    def __init__(
        self,
        weights_path: str = "yolo11s.pt",
        conf_threshold: float = 0.4,
        device: str = "cuda",
        target_labels: Sequence[str] = ("person", "train"),
    ):
        self.model = YOLO(weights_path)
        self.conf_threshold = conf_threshold
        self.device = device
        self.target_labels = set(target_labels)
        self.label_to_id = {name: idx for idx, name in self.model.names.items()}
        self.target_ids = [
            self.label_to_id[label]
            for label in self.target_labels
            if label in self.label_to_id
        ]

    def detect(self, frame: np.ndarray) -> List[Detection]:
        if self.target_ids:
            results = self.model.predict(
                source=frame,
                imgsz=640,
                conf=self.conf_threshold,
                device=self.device,
                classes=self.target_ids,
                verbose=False,
            )
        else:
            results = self.model.predict(
                source=frame,
                imgsz=640,
                conf=self.conf_threshold,
                device=self.device,
                verbose=False,
            )

        detections: List[Detection] = []
        result = results[0]
        if result.boxes is None:
            return detections

        for box in result.boxes:
            cls_id = int(box.cls.item())
            score = float(box.conf.item())
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            label = self.model.names.get(cls_id, str(cls_id))
            detections.append(
                Detection(
                    bbox=(int(x1), int(y1), int(x2), int(y2)),
                    score=score,
                    class_id=cls_id,
                    label=label,
                )
            )
        return detections
