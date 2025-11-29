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

The `--save-crops` option writes each detected person crop (from frames where detection is run) into the specified directory using the pattern `frame<frame>_det<idx>_person.jpg`. Crops are taken from the raw frame without the green detection box to avoid margins. You can then sort these crops into six uniform folders to train your classifier, including multi-colored uniforms.
