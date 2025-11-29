# cv_mirea_hack

Utilities for running YOLO-based detection on videos.

## Video inference

To draw detections and optionally save cropped people for uniform-classification dataset preparation:

```bash
python -m detection.video_inference \
  --input path/to/input.mp4 \
  --output path/to/output.mp4 \
  --frame-stride 3 \
  --device cuda \
  --save-crops crops/persons
```
