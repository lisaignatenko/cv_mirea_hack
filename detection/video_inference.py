from pathlib import Path
from typing import Optional, List

import cv2

from detection.detector import FactoryDetector, Detection


def run_video(
    input_path: str,
    output_path: Optional[str] = None,
    frame_stride: int = 3,
    show: bool = False,
    device: str = "cuda",
):
    print(f"Opening video: {input_path}")
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {input_path}")

    detector = FactoryDetector(device=device, target_labels=("person", "train"))
    frame_idx = 0
    detections: List[Detection] = []
    writer = None
    output_path_obj = Path(output_path) if output_path is not None else None

    while True:
        ret, frame = cap.read()
        if not ret:
            print("No more frames, stopping")
            break

        if writer is None and output_path_obj is not None:
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            fps = cap.get(cv2.CAP_PROP_FPS)
            if not fps or fps <= 1e-2:
                fps = 25.0
            h, w = frame.shape[:2]
            writer = cv2.VideoWriter(
                str(output_path_obj),
                fourcc,
                max(fps / max(frame_stride, 1), 1.0),
                (w, h),
            )
            if not writer.isOpened():
                raise RuntimeError("Failed to open VideoWriter")

        if frame_idx % frame_stride == 0:
            print(f"Processing frame {frame_idx}")
            detections = detector.detect(frame)

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = (0, 255, 0) if det.label == "person" else (255, 0, 0)
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

        if writer is not None:
            writer.write(frame)

        if show:
            cv2.imshow("detections", frame)
            key = cv2.waitKey(1)
            if key == 27:
                break

        frame_idx += 1

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
    args = parser.parse_args()

    run_video(
        input_path=args.input,
        output_path=args.output,
        frame_stride=args.frame_stride,
        show=args.show,
        device=args.device,
    )


if __name__ == "__main__":
    main()
