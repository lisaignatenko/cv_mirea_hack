from __future__ import annotations

import argparse

from .video import run_video


def main() -> None:
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
    parser.add_argument(
        "--jsonl-path",
        type=str,
        default="frames.jsonl",
        help="Path to JSONL with per-frame metadata",
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
        jsonl_path=args.jsonl_path,
    )


if __name__ == "__main__":
    main()
