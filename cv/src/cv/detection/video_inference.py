from pathlib import Path
from typing import List, Optional

import cv2

from cv.detection.detector import Detection, FactoryDetector


def run_video(
    input_path: str,
    output_path: Optional[str] = None,
    frame_stride: int = 3,
    show: bool = False,
    device: str = "cuda",
    save_crops_dir: Optional[str] = None,
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
    crops_dir = Path(save_crops_dir) if save_crops_dir is not None else None
    if crops_dir is not None:
        crops_dir.mkdir(parents=True, exist_ok=True)

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

        should_run_detection = frame_idx % frame_stride == 0
        if should_run_detection:
            print(f"Processing frame {frame_idx}")
            detections = detector.detect(frame)

        for det_idx, det in enumerate(detections):
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

            if crops_dir is not None and should_run_detection and det.label == "person":
                crop_x1 = max(0, x1)
                crop_y1 = max(0, y1)
                crop_x2 = min(frame.shape[1], x2)
                crop_y2 = min(frame.shape[0], y2)
                if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                    crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                    crop_name = f"frame{frame_idx:06d}_det{det_idx:03d}_{det.label}.jpg"
                    cv2.imwrite(str(crops_dir / crop_name), crop)

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
    parser.add_argument(
        "--save-crops",
        type=str,
        help="Directory to save cropped person images for dataset creation",
    )
    args = parser.parse_args()

    run_video(
        input_path=args.input,
        output_path=args.output,
        frame_stride=args.frame_stride,
        show=args.show,
        device=args.device,
        save_crops_dir=args.save_crops,
    )


if __name__ == "__main__":
    main()
