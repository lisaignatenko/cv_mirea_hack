# ocr.py
from dataclasses import dataclass
from datetime import datetime, timezone
import cv2
import re
from rapidocr_onnxruntime import RapidOCR

TIMESTAMP_ROI = (4, 0, 490, 59)


@dataclass
class OCRResult:
    timestamp: datetime | None
    confidence: float


class TimestampOCR:
    def __init__(self, conf_threshold: float = 0.3):
        """Initialize OCR engine for timestamp recognition."""
        self.ocr = RapidOCR()
        self.conf_threshold = conf_threshold

    def parse_timestamp(self, text: str) -> datetime | None:
        """Parse OCR text into timezone-aware UTC datetime."""
        if not text:
            return None

        text = text.upper()
        text = text.translate(
            str.maketrans(
                {
                    "O": "0",
                    "I": "1",
                    "L": "1",
                    "S": "5",
                    "B": "8",
                }
            )
        )

        cleaned = re.sub(r"[^0-9:\- ]", "", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            return None

        candidates: list[str] = [cleaned]

        m = re.match(r"(\d{4}-\d{2}-\d{2})(\d{2}:\d{2}:\d{2})", cleaned)
        if m:
            candidates.append(f"{m.group(1)} {m.group(2)}")

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%H:%M:%S",
            "%H:%M",
            "%Y%m%d-%H%M%S",
            "%Y%m%d%H%M%S",
            "%H%M%S",
        ]

        for s in candidates:
            for fmt in formats:
                try:
                    dt = datetime.strptime(s, fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue

        return None

    def _preprocess(self, roi):
        """Preprocess ROI for more robust OCR under varying lighting."""
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        return gray

    def recognize(self, frame) -> OCRResult:
        """Recognize timestamp from video frame and return OCRResult."""
        x1, y1, x2, y2 = TIMESTAMP_ROI
        roi = frame[y1:y2, x1:x2]

        gray = self._preprocess(roi)
        ocr_inputs = [gray, cv2.bitwise_not(gray)]

        best_ts: datetime | None = None
        best_conf: float = 0.0

        for img in ocr_inputs:
            result, _ = self.ocr(img)
            if not result:
                continue

            texts = [r[1] for r in result]
            confs = [r[2] for r in result]

            full_text = "".join(texts)
            avg_conf = float(sum(confs) / len(confs)) if confs else 0.0

            ts = self.parse_timestamp(full_text)
            if ts is not None and avg_conf > best_conf:
                best_ts = ts
                best_conf = avg_conf

        if best_ts is None or best_conf < self.conf_threshold:
            return OCRResult(timestamp=None, confidence=best_conf)

        return OCRResult(timestamp=best_ts, confidence=best_conf)
