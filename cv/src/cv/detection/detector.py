import json
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from ultralytics import YOLO


@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]
    score: float
    class_id: int
    label: str
    track_id: Optional[int] = None


@dataclass
class DangerZone:
    points: List[Tuple[int, int]]
    name: str
    safe_distance: float = 45.0


@dataclass
class PersonMetrics:
    track_id: int
    detection_count: int = 0
    violation_count: int = 0
    min_distance: float = float("inf")
    total_danger_time: float = 0.0  # суммарное время в опасной зоне (сек)
    last_danger_time: Optional[float] = None  # оставлено для совместимости, сейчас не используем
    is_in_danger: bool = False
    first_detection_time: Optional[float] = None
    last_detection_time: Optional[float] = None
    dominant_color: Optional[Tuple[int, int, int]] = None
    last_foot_point: Optional[Tuple[int, int]] = None
    color_history: deque = None

    def __post_init__(self):
        if self.color_history is None:
            self.color_history = deque(maxlen=10)


class SimpleTracker:
    def __init__(self, max_distance: float = 100.0, max_missed_frames: int = 15):
        self.max_distance = max_distance
        self.max_missed_frames = max_missed_frames
        self.tracks: Dict[int, PersonMetrics] = {}  # track_id -> PersonMetrics
        self.next_id: int = 0
        self.missed_frames: Dict[int, int] = defaultdict(int)

    def get_foot_point(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) // 2, y2)

    def extract_dominant_color(
        self, frame: np.ndarray, bbox: Tuple[int, int, int, int]
    ) -> Tuple[int, int, int]:
        """
        Извлекает доминирующий (средний) цвет из верхней части bounding box,
        предполагая, что там одежда.
        """
        x1, y1, x2, y2 = bbox

        height = y2 - y1
        if height <= 0 or x2 <= x1:
            return (128, 128, 128)

        clothing_region = frame[y1 : y1 + max(1, height // 3), x1:x2]

        if clothing_region.size == 0:
            return (128, 128, 128)

        avg_color = np.mean(clothing_region, axis=(0, 1))
        return tuple(map(int, avg_color))  # BGR

    def calculate_similarity(
        self, color1: Tuple[int, int, int], color2: Tuple[int, int, int]
    ) -> float:
        """Вычисляет схожесть цветов (0-1, где 1 - одинаковые). Сейчас не используется."""
        if color1 is None or color2 is None:
            return 0.0

        diff = np.array(color1, dtype=float) - np.array(color2, dtype=float)
        distance = float(np.sqrt(np.sum(diff**2)))
        max_distance = 441.67  # sqrt(3 * 255^2)
        return max(0.0, 1.0 - distance / max_distance)

    def update(self, detections: List[Detection], frame: np.ndarray, frame_time: float) -> None:
        """
        Обновляет треки на основе новых детекций.
        frame_time — "глобальное" время (в секундах) на момент обработки кадра.
        """
        person_detections = [det for det in detections if det.label == "person"]

        # если людей нет — увеличиваем missed_frames и удаляем старые треки
        if not person_detections:
            for track_id in list(self.tracks.keys()):
                self.missed_frames[track_id] += 1
                if self.missed_frames[track_id] > self.max_missed_frames:
                    del self.tracks[track_id]
                    del self.missed_frames[track_id]
            return

        # подготовка текущих детекций
        current_detections = []
        for det in person_detections:
            foot_point = self.get_foot_point(det.bbox)
            dominant_color = self.extract_dominant_color(frame, det.bbox)
            current_detections.append(
                {
                    "detection": det,
                    "foot_point": foot_point,
                    "color": dominant_color,
                }
            )

        matched_detections = set()
        matched_tracks = set()

        # сопоставление по расстоянию между точками ног
        for track_id, metrics in list(self.tracks.items()):
            if self.missed_frames[track_id] > self.max_missed_frames:
                continue

            best_match_idx = None
            best_distance = float("inf")

            for i, det_info in enumerate(current_detections):
                if i in matched_detections:
                    continue

                if metrics.last_foot_point is not None:
                    distance = float(
                        np.linalg.norm(
                            np.array(det_info["foot_point"], dtype=float)
                            - np.array(metrics.last_foot_point, dtype=float)
                        )
                    )

                    if distance < best_distance and distance < self.max_distance:
                        best_distance = distance
                        best_match_idx = i

            if best_match_idx is not None:
                det_info = current_detections[best_match_idx]
                det = det_info["detection"]
                det.track_id = track_id

                metrics.detection_count += 1
                metrics.last_detection_time = frame_time
                metrics.last_foot_point = det_info["foot_point"]
                metrics.dominant_color = det_info["color"]
                metrics.color_history.append(det_info["color"])

                matched_detections.add(best_match_idx)
                matched_tracks.add(track_id)
                self.missed_frames[track_id] = 0

        # создание новых треков
        for i, det_info in enumerate(current_detections):
            if i not in matched_detections:
                new_track_id = self.next_id
                self.next_id += 1

                det = det_info["detection"]
                det.track_id = new_track_id

                self.tracks[new_track_id] = PersonMetrics(
                    track_id=new_track_id,
                    detection_count=1,
                    first_detection_time=frame_time,
                    last_detection_time=frame_time,
                    dominant_color=det_info["color"],
                    last_foot_point=det_info["foot_point"],
                )
                self.missed_frames[new_track_id] = 0
                matched_tracks.add(new_track_id)

        # увеличиваем missed_frames только для тех, кто в этот кадр не попал
        for track_id in list(self.tracks.keys()):
            if track_id not in matched_tracks:
                self.missed_frames[track_id] += 1

        # удаляем старые треки
        tracks_to_remove = [
            track_id
            for track_id in self.tracks
            if self.missed_frames[track_id] > self.max_missed_frames
        ]
        for track_id in tracks_to_remove:
            del self.tracks[track_id]
            del self.missed_frames[track_id]


class FactoryDetector:
    def __init__(
        self,
        weights_path: str = "yolo11s.pt",
        conf_threshold: float = 0.25,
        motion_conf_threshold: float | None = None,
        motion_iou_threshold: float = 0.2,
        device: str = "cuda",
        target_labels: Sequence[str] = ("person", "train"),
        tracking_enabled: bool = True,
    ):
        """Factory safety detector built on top of YOLO with tracking and danger zones."""
        self.model = YOLO(weights_path)
        self.conf_threshold = conf_threshold
        self.motion_conf_threshold = (
            motion_conf_threshold
            if motion_conf_threshold is not None
            else max(conf_threshold + 0.15, conf_threshold)
        )
        self.motion_iou_threshold = motion_iou_threshold
        self.device = device
        self.target_labels = set(target_labels)
        self.label_to_id = {name: idx for idx, name in self.model.names.items()}
        self.target_ids = [
            self.label_to_id[label] for label in self.target_labels if label in self.label_to_id
        ]

        self.tracker: Optional[SimpleTracker] = SimpleTracker() if tracking_enabled else None
        self.tracking_enabled = tracking_enabled

        self.danger_zones: List[DangerZone] = self.load_danger_zones()

        self.frame_count: int = 0
        self.total_violations: int = 0
        self.fps: float = 25.0
        self.time_seconds: float = 0.0

    def set_fps(self, fps: float) -> None:
        """Set video FPS for correct time integration."""
        if fps and fps > 1e-3:
            self.fps = float(fps)
        else:
            self.fps = 25.0

    def load_danger_zones(self) -> List[DangerZone]:
        """Load danger zones polygons from JSON or return defaults."""
        default_zones = [
            DangerZone(
                points=[(100, 500), (300, 500), (300, 700), (100, 700)],
                name="Railway Track 1",
                safe_distance=100.0,
            ),
            DangerZone(
                points=[(500, 500), (700, 500), (700, 700), (500, 700)],
                name="Railway Track 2",
                safe_distance=100.0,
            ),
        ]

        try:
            with open("danger_zones.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            zones_data = data.get("zones")
            if not isinstance(zones_data, list):
                raise ValueError("Поле 'zones' должно быть списком")

            danger_zones: List[DangerZone] = []
            for i, zone in enumerate(zones_data):
                if isinstance(zone, dict):
                    points = zone.get("points")
                    if not points:
                        continue
                    name = zone.get("name", f"Zone {i + 1}")
                    safe_distance = float(zone.get("safe_distance", 100.0))
                else:
                    points = zone
                    name = f"Zone {i + 1}"
                    safe_distance = 100.0

                points_tuples = [tuple(map(int, p)) for p in points]
                if len(points_tuples) < 2:
                    continue

                danger_zones.append(
                    DangerZone(points=points_tuples, name=name, safe_distance=safe_distance)
                )

            if not danger_zones:
                raise ValueError("Не удалось загрузить ни одной валидной зоны")

            return danger_zones

        except (FileNotFoundError, ValueError, KeyError, TypeError):
            return default_zones

    def bbox_iou(self, b1: Tuple[int, int, int, int], b2: Tuple[int, int, int, int]) -> float:
        """Compute IoU between two bounding boxes."""
        x11, y11, x12, y12 = b1
        x21, y21, x22, y22 = b2

        xi1 = max(x11, x21)
        yi1 = max(y11, y21)
        xi2 = min(x12, x22)
        yi2 = min(y12, y22)

        iw = max(0, xi2 - xi1)
        ih = max(0, yi2 - yi1)
        inter = iw * ih

        if inter <= 0:
            return 0.0

        a1 = (x12 - x11) * (y12 - y11)
        a2 = (x22 - x21) * (y22 - y21)
        union = a1 + a2 - inter
        if union <= 0:
            return 0.0

        return float(inter / union)

    def _filter_detections_by_motion(
        self,
        detections: List[Detection],
        motion_boxes: Optional[Sequence[Tuple[int, int, int, int]]],
    ) -> List[Detection]:
        """Apply dual-threshold filtering: high conf for static, low conf for motion-overlapping."""
        if not motion_boxes:
            return detections

        filtered: List[Detection] = []
        for det in detections:
            if det.label not in ("person", "train"):
                filtered.append(det)
                continue

            score = det.score

            if score >= self.motion_conf_threshold:
                filtered.append(det)
                continue

            if score < self.conf_threshold:
                continue

            keep = False
            for mb in motion_boxes:
                if self.bbox_iou(det.bbox, mb) >= self.motion_iou_threshold:
                    keep = True
                    break

            if keep:
                filtered.append(det)

        return filtered

    def detect(
        self,
        frame: np.ndarray,
        motion_boxes: Optional[Sequence[Tuple[int, int, int, int]]] = None,
    ) -> List[Detection]:
        """Run YOLO detector and return filtered list of Detection objects, optionally using motion priors."""
        if self.target_ids:
            results = self.model.predict(
                source=frame,
                imgsz=960,
                conf=self.conf_threshold,
                device=self.device,
                classes=self.target_ids,
                verbose=False,
            )
        else:
            results = self.model.predict(
                source=frame,
                imgsz=960,
                conf=self.conf_threshold,
                device=self.device,
                verbose=False,
            )

        detections: List[Detection] = []
        result = results[0]
        if result.boxes is None:
            final_detections: List[Detection] = []
        else:
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

            final_detections = self._filter_detections_by_motion(detections, motion_boxes)

        if self.tracking_enabled and self.tracker is not None:
            frame_time = self.time_seconds
            self.tracker.update(final_detections, frame, frame_time)

        return final_detections

    def calculate_distance_to_zone(self, point: Tuple[int, int], zone: DangerZone) -> float:
        """Compute minimum distance from point to polygon edges."""
        if not zone.points or len(zone.points) < 2:
            return float("inf")

        point_array = np.array(point, dtype=float)
        zone_array = np.array(zone.points, dtype=float)
        min_distance = float("inf")

        for i in range(len(zone_array)):
            p1 = zone_array[i]
            p2 = zone_array[(i + 1) % len(zone_array)]

            line_vec = p2 - p1
            line_len_sq = float(np.dot(line_vec, line_vec))
            if line_len_sq == 0.0:
                continue

            t = float(np.dot(point_array - p1, line_vec) / line_len_sq)
            t = max(0.0, min(1.0, t))

            nearest = p1 + t * line_vec
            distance = float(np.linalg.norm(point_array - nearest))

            if distance < min_distance:
                min_distance = distance

        return min_distance

    def get_person_foot_point(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """Return bottom-center point of a person bbox."""
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) // 2, y2)

    def check_safety_distances(
        self,
        detections: List[Detection],
        fps: Optional[float] = None,
    ) -> List[Tuple[Detection, DangerZone, float]]:
        """Check minimal distance of each person to all danger zones and update metrics."""
        if fps is not None:
            self.set_fps(fps)

        dt = 1.0 / self.fps

        warnings: List[Tuple[Detection, DangerZone, float]] = []

        for detection in detections:
            if detection.label != "person":
                continue

            foot_point = self.get_person_foot_point(detection.bbox)

            metrics: Optional[PersonMetrics] = None
            if (
                self.tracking_enabled
                and self.tracker is not None
                and detection.track_id is not None
            ):
                metrics = self.tracker.tracks.get(detection.track_id)

            min_distance = float("inf")
            closest_zone: Optional[DangerZone] = None

            for zone in self.danger_zones:
                distance = self.calculate_distance_to_zone(foot_point, zone)
                if distance < min_distance:
                    min_distance = distance
                    closest_zone = zone

            if metrics is not None:
                metrics.min_distance = min(metrics.min_distance, min_distance)

                if closest_zone is not None and min_distance < closest_zone.safe_distance:
                    warnings.append((detection, closest_zone, min_distance))
                    metrics.is_in_danger = True
                    metrics.violation_count += 1
                else:
                    metrics.is_in_danger = False

        if self.tracking_enabled and self.tracker is not None:
            for metrics in self.tracker.tracks.values():
                if metrics.is_in_danger:
                    metrics.total_danger_time += dt

        self.total_violations += len(warnings)
        self.frame_count += 1
        self.time_seconds += dt

        return warnings

    def get_metrics_summary(self) -> Dict:
        """Return aggregated tracking and safety metrics."""
        if not self.tracking_enabled or self.tracker is None:
            return {
                "total_unique_people": 0,
                "people_in_danger_zone": 0,
                "total_violations": self.total_violations,
                "total_processing_frames": self.frame_count,
                "current_time_seconds": self.time_seconds,
                "error": "Tracking not enabled",
            }

        tracks = list(self.tracker.tracks.values())
        total_people = len(tracks)
        people_in_danger = sum(1 for m in tracks if m.violation_count > 0)

        if total_people > 0:
            avg_detection_count = float(np.mean([m.detection_count for m in tracks]))
            avg_violation_count = float(np.mean([m.violation_count for m in tracks]))
            avg_danger_time = float(np.mean([m.total_danger_time for m in tracks]))
        else:
            avg_detection_count = 0.0
            avg_violation_count = 0.0
            avg_danger_time = 0.0

        track_durations = []
        for m in tracks:
            if m.first_detection_time is not None and m.last_detection_time is not None:
                duration = float(m.last_detection_time - m.first_detection_time)
                track_durations.append(duration)

        avg_track_duration = float(np.mean(track_durations)) if track_durations else 0.0

        detailed_metrics = {
            track_id: {
                "detection_count": m.detection_count,
                "violation_count": m.violation_count,
                "min_distance_to_zone": float(m.min_distance),
                "total_danger_time_seconds": float(m.total_danger_time),
                "track_duration_seconds": (
                    float(m.last_detection_time - m.first_detection_time)
                    if m.first_detection_time is not None and m.last_detection_time is not None
                    else 0.0
                ),
                "dominant_color": m.dominant_color,
            }
            for track_id, m in self.tracker.tracks.items()
        }

        return {
            "total_unique_people": total_people,
            "people_in_danger_zone": people_in_danger,
            "total_violations": self.total_violations,
            "average_detections_per_person": avg_detection_count,
            "average_violations_per_person": avg_violation_count,
            "average_time_in_danger_seconds": avg_danger_time,
            "average_track_duration_seconds": avg_track_duration,
            "total_processing_frames": self.frame_count,
            "current_time_seconds": self.time_seconds,
            "detailed_metrics": detailed_metrics,
        }

    def draw_danger_zones(self, frame: np.ndarray) -> None:
        """Draw all configured danger zones on frame."""
        for zone in self.danger_zones:
            if not zone.points:
                continue

            points = np.array(zone.points, np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [points], True, (0, 0, 255), 2)

            cv2.putText(
                frame,
                f"{zone.name} ({zone.safe_distance}px)",
                zone.points[0],
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
            )

