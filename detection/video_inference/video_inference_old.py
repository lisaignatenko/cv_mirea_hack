from pathlib import Path
from typing import Optional, List, Union
import cv2
import numpy as np
import json
from datetime import datetime, timezone
from PIL import Image
import re
from cv_mirea_hack.detection.detector import FactoryDetector, Detection
import easyocr

TIMESTAMP_ROI = (1, 1, 615, 38)

_reader = None

def get_reader():
    global _reader
    if _reader is None:
        print("Инициализация EasyOCR...")
        _reader = easyocr.Reader(['en'])  # Только английский для цифр
    return _reader

def extract_timestamp_from_frame(frame) -> Optional[datetime]:  # ИСПРАВЛЕНО: | -> Optional
    x1, y1, x2, y2 = TIMESTAMP_ROI
    roi = frame[y1:y2, x1:x2]
    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
    
    # Получаем ридер
    reader = get_reader()
    
    # ПРОСТАЯ предобработка для EasyOCR
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Увеличиваем контраст
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
    
    # Используем EasyOCR
    results = reader.readtext(gray, 
                            allowlist='0123456789-: ',  # Разрешаем только нужные символы
                            paragraph=False, 
                            detail=1)
    
    # Собираем все распознанные тексты
    texts = []
    for (bbox, text, confidence) in results:
        if confidence > 0.3:  # Фильтруем по уверенности
            texts.append(text.strip())
            print(f"EASY_OCR: '{text}' (confidence: {confidence:.2f})")
    
    if not texts:
        print("EASY_OCR: Текст не распознан")
        return None
    
    # Объединяем все распознанные части
    full_text = ' '.join(texts)
    print(f"EASY_OCR: Объединенный текст: '{full_text}'")
    
    # Очищаем текст - оставляем только цифры, дефисы и двоеточия
    cleaned_text = re.sub(r'[^\d:-]', '', full_text)
    print(f"EASY_OCR: Очищенный текст: '{cleaned_text}'")
    
    if not cleaned_text:
        return None
    
    # ГИБКИЙ ПАРСИНГ разных форматов времени
    time_formats = [
        "%Y-%m-%d %H:%M:%S",    # 2024-01-15 14:30:25
        "%H:%M:%S",             # 14:30:25
        "%Y%m%d-%H%M%S",        # 20240115-143025
        "%Y%m%d%H%M%S",         # 20240115143025
        "%H%M%S",               # 143025
        "%Y-%m-%d %H:%M",       # 2024-01-15 14:30
        "%H:%M",                # 14:30
    ]
    
    for fmt in time_formats:
        try:
            # Для форматов с пробелами - добавляем пробелы в очищенный текст
            text_to_parse = cleaned_text
            if ' ' in fmt:
                # Пытаемся вставить пробелы в нужные места
                if len(cleaned_text) >= 10:
                    text_to_parse = f"{cleaned_text[:10]} {cleaned_text[10:]}"
            
            dt = datetime.strptime(text_to_parse, fmt)
            dt = dt.replace(tzinfo=timezone.utc)
            print(f"EASY_OCR: УСПЕХ! Распознано время: {dt} (формат: {fmt})")
            return dt
        except ValueError:
            continue
    
    print(f"EASY_OCR: Не удалось распарсить: '{cleaned_text}'")
    return None

def build_frame_json(
    timestamp_iso: Optional[str],  # ИСПРАВЛЕНО: | -> Optional
    camera_id: str,
    tick: int,
    detections: List[Detection],   # ИСПРАВЛЕНО: list -> List
    safety_warnings,
    detector: FactoryDetector,
) -> dict:
    # -------- TRAIN ----------
    train_dets = [d for d in detections if d.label == "train"]
    if train_dets:
        train_det = max(
            train_dets,
            key=lambda d: (d.bbox[2] - d.bbox[0]) * (d.bbox[3] - d.bbox[1]),
        )
        x1, y1, x2, y2 = train_det.bbox
        train_part = {
            "is_present": True,
            "status": "standing",  # заглушка
            "train_id": "train_1",
            "bbox": {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
            },
            "confidence": {
                "detection": float(train_det.score),
                "status": 0.5,  # заглушка
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

    # -------- PEOPLE ----------
    people = []
    for det in detections:
        if det.label != "person":
            continue

        x1, y1, x2, y2 = det.bbox

        is_in_danger = any(w[0] is det for w in safety_warnings)

        person_json = {
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

    # -------- EVENTS ----------
    events = []  # пока пустой список

    frame_json = {
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
    output_path: Optional[str] = None,
    frame_stride: int = 3,
    show: bool = False,
    device: str = "cuda",
    save_metrics: bool = True,
    tracking: bool = True,
):
    print(f"Opening video: {input_path}")
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {input_path}")

    detector = FactoryDetector(
        device=device,
        target_labels=("person", "train"),
        tracking_enabled=tracking,
    )

    # FPS исходного видео
    raw_fps = cap.get(cv2.CAP_PROP_FPS)
    if not raw_fps or raw_fps <= 1e-2:
        raw_fps = 25.0

    # ЭФФЕКТИВНЫЙ FPS для обработки, учитывая frame_stride
    effective_fps = raw_fps / max(frame_stride, 1)

    detector.set_fps(effective_fps)

    print(f"Video FPS (raw): {raw_fps}")
    print(f"Frame stride: {frame_stride}")
    print(f"Effective FPS for processing: {effective_fps}")
    print(f"Tracking enabled: {tracking}")

    frame_idx = 0
    detections: List[Detection] = []  # ИСПРАВЛЕНО: list -> List
    safety_warnings = []
    writer = None
    output_path_obj = Path(output_path) if output_path is not None else None

    # файл для JSONL (по желанию)
    jsonl_file = open("frames.jsonl", "w", encoding="utf-8")

    # Цвета для разных треков
    track_colors = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            print("No more frames, stopping")
            break

        # Ленивая инициализация VideoWriter
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

        # Обрабатываем только каждый N-й кадр
        if frame_idx % frame_stride == 0:
            print(f"Processing frame {frame_idx}")

            # 1) достаём время с кадра
            frame_dt = extract_timestamp_from_frame(frame)
            if frame_dt is not None:
                timestamp_iso = frame_dt.isoformat().replace("+00:00", "Z")
            else:
                timestamp_iso = None

            # 2) обычная детекция
            detections = detector.detect(frame)
            safety_warnings = detector.check_safety_distances(detections)

            # 3) собираем JSON для этого кадра
            frame_json = build_frame_json(
                timestamp_iso=timestamp_iso,
                camera_id="camera_1",
                tick=frame_idx,
                detections=detections,
                safety_warnings=safety_warnings,
                detector=detector,
            )
            jsonl_file.write(json.dumps(frame_json, ensure_ascii=False) + "\n")

        # Рисуем опасные зоны
        detector.draw_danger_zones(frame)

        # Отрисовка детекций
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

                if detector.tracking_enabled and detector.tracker and det.track_id is not None:
                    metrics = detector.tracker.tracks.get(det.track_id)
                    if metrics and metrics.dominant_color:
                        color_rect_size = 20
                        color_x = x2 + 5
                        color_y = y1
                        cv2.rectangle(
                            frame,
                            (color_x, color_y),
                            (color_x + color_rect_size, color_y + color_rect_size),
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

        # Рисуем предупреждения
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

        current_metrics = detector.get_metrics_summary()

        if writer is not None:
            writer.write(frame)

        if show:
            cv2.imshow("Safety Monitoring with Tracking", frame)
            key = cv2.waitKey(1)
            if key == 27:  # ESC
                break
            elif key == ord("p"):
                cv2.waitKey(0)
            elif key == ord("t"):
                pass

        frame_idx += 1

    # Финальные метрики
    final_metrics = detector.get_metrics_summary()

    print("\n" + "=" * 50)
    print("FINAL SAFETY METRICS SUMMARY")
    print("=" * 50)
    print(f"Total unique people: {final_metrics.get('total_unique_people', 0)}")
    print(f"People in danger zones: {final_metrics.get('people_in_danger_zone', 0)}")
    print(f"Total safety violations: {final_metrics.get('total_violations', 0)}")
    print(
        "Average track duration: "
        f"{final_metrics.get('average_track_duration_seconds', 0):.2f}s"
    )
    print(
        "Average time in danger: "
        f"{final_metrics.get('average_time_in_danger_seconds', 0):.2f}s"
    )
    print(f"Total frames processed: {final_metrics.get('total_processing_frames', 0)}")
    print(f"Total time (s): {final_metrics.get('current_time_seconds', 0):.2f}")

    if save_metrics:
        metrics_filename = f"safety_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(metrics_filename, "w", encoding="utf-8") as f:
            json.dump(final_metrics, f, indent=2, ensure_ascii=False)
        print(f"\nDetailed metrics saved to: {metrics_filename}")

    jsonl_file.close()
    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()
    print("Done")

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to input video")
    parser.add_argument("--output", help="Path to output video with boxes")
    parser.add_argument(
        "--frame-stride",
        type=int,
        default=3,
        help="Process every N-th frame",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Device for model: cuda or cpu",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show window with video",
    )
    parser.add_argument(
        "--no-metrics",
        action="store_true",
        help="Don't save metrics to file",
    )
    parser.add_argument(
        "--no-tracking",
        action="store_true",
        help="Disable person tracking",
    )
    args = parser.parse_args()

    run_video(
        input_path=args.input,
        output_path=args.output,
        frame_stride=args.frame_stride,
        show=args.show,
        device=args.device,
        save_metrics=not args.no_metrics,
        tracking=not args.no_tracking,
    )

if __name__ == "__main__":
    main()