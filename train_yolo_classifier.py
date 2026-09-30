"""
Train the YOLOv8 classification model for crop leaf diseases.

    python scripts/prepare_dataset.py          # once: balanced train/val split
    python train_yolo_classifier.py            # train (defaults are CPU friendly)

Common options:
    --epochs 20  --imgsz 224  --batch 32  --workers 4
    --weights yolov8n.pt          initial weights (see below)
    --resume                      continue an interrupted run
    --data datasets/other_prepared

Initial weights
    *-cls.pt (e.g. yolov8n-cls.pt)  used as they are.
    a detection checkpoint (e.g. yolov8n.pt, the file in the project root): its
    backbone is transferred into a fresh classification model.

Output
    app/ai/models/yolov8_disease.pt            best weights (used by the backend)
    app/ai/models/yolov8_disease_metrics.json  accuracy, classes, settings
    runs/disease/                              training logs / last.pt (resume)

If --data has no train/ and val/ folders, the raw class folders are prepared
first with the same balanced split as scripts/prepare_dataset.py.
"""

import argparse
import json
import os
import shutil
import sys
import time

DEFAULT_RAW = "datasets/leaf_disease_detection_dataset"
DEFAULT_PREPARED = "datasets/prepared"
OUT_WEIGHTS = "app/ai/models/yolov8_disease.pt"
OUT_METRICS = "app/ai/models/yolov8_disease_metrics.json"
RUNS_DIR = os.path.abspath("runs")
RUN_NAME = "disease"


def default_weights():
    for candidate in ("yolov8n.pt", "yolov8n-cls.pt"):
        if os.path.exists(candidate):
            return candidate

    return "yolov8n-cls.pt"            # ultralytics downloads it


def build_model(weights):
    """A YOLOv8 classification model initialised from `weights`."""

    from ultralytics import YOLO

    name = os.path.basename(weights).lower()

    if name.endswith("-cls.pt"):
        return YOLO(weights)

    # Detection checkpoint: build the matching classification network from
    # its YAML and transfer every layer whose shape fits (the backbone).
    size = name[len("yolov8")] if name.startswith("yolov8") else "n"

    model = YOLO(f"yolov8{size}-cls.yaml")
    model.load(weights)

    return model


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8-cls for crop diseases")
    parser.add_argument("--data", default=None, help="prepared dataset (train/ + val/) or raw class folders")
    parser.add_argument("--weights", default=None)
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--patience", type=int, default=5, help="stop after this many epochs without improvement")
    parser.add_argument("--device", default=None, help="cpu, 0 (first GPU) ... default: automatic")
    parser.add_argument("--max-train", type=int, default=500, help="images per class when preparing raw data")
    parser.add_argument("--max-val", type=int, default=100)
    parser.add_argument("--resume", action="store_true", help="continue runs/disease/weights/last.pt")
    parser.add_argument("--out", default=OUT_WEIGHTS)
    args = parser.parse_args()

    from ultralytics import YOLO

    # ---- resume -----------------------------------------------------------
    last = os.path.join(RUNS_DIR, RUN_NAME, "weights", "last.pt")

    if args.resume:
        if not os.path.exists(last):
            raise SystemExit(f"Nothing to resume: {last} does not exist")

        model = YOLO(last)
        data_dir = None

    else:
        # ---- dataset ------------------------------------------------------
        data_dir = args.data or DEFAULT_PREPARED

        has_split = (
            os.path.isdir(os.path.join(data_dir, "train"))
            and os.path.isdir(os.path.join(data_dir, "val"))
        )

        if not has_split:
            raw = args.data or DEFAULT_RAW

            if not os.path.isdir(raw):
                raise SystemExit(
                    f"Dataset folder not found: {raw}\n"
                    "Put one folder per class inside it (Crop___disease/*.jpg)."
                )

            from app.ai.training.prepare import prepare_dataset

            data_dir = DEFAULT_PREPARED if not args.data else args.data.rstrip("/\\") + "_prepared"

            print(f"Preparing the dataset from {raw} -> {data_dir}")
            prepare_dataset(raw, data_dir, max_train=args.max_train, max_val=args.max_val)

        model = build_model(args.weights or default_weights())

    started = time.time()

    # ---- train ------------------------------------------------------------
    if args.resume:
        model.train(resume=True)

    else:
        model.train(
            data=os.path.abspath(data_dir),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            workers=args.workers,
            patience=args.patience,
            device=args.device,
            project=RUNS_DIR,
            name=RUN_NAME,
            exist_ok=True,
            plots=False,
            flipud=0.5,             # a leaf has no "up"
            fliplr=0.5,
            verbose=True,
        )

    best = os.path.join(RUNS_DIR, RUN_NAME, "weights", "best.pt")

    if not os.path.exists(best):
        raise SystemExit("Training finished but best.pt was not created")

    # ---- final accuracy of the saved weights --------------------------------
    best_model = YOLO(best)
    data_dir = data_dir or os.path.abspath(DEFAULT_PREPARED)

    metrics = best_model.val(
        data=os.path.abspath(data_dir),
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        device=args.device,
        plots=False,
        verbose=False,
        project=RUNS_DIR,
        name="validation",
        exist_ok=True,
    )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    shutil.copy2(best, args.out)

    summary = {
        "weights": args.out,
        "classes": list(best_model.names.values()),
        "top1_accuracy": round(float(metrics.top1), 4),
        "top5_accuracy": round(float(metrics.top5), 4),
        "epochs_requested": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "initial_weights": args.weights or default_weights(),
        "train_minutes": round((time.time() - started) / 60, 1),
        "dataset_report": os.path.join(data_dir, "dataset_report.json"),
    }

    with open(OUT_METRICS, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n==============================================")
    print(f"Saved weights: {args.out}")
    print(f"Classes: {len(summary['classes'])}")
    print(f"Top-1 accuracy: {summary['top1_accuracy'] * 100:.2f}%")
    print(f"Top-5 accuracy: {summary['top5_accuracy'] * 100:.2f}%")
    print(f"Training time: {summary['train_minutes']} minutes")
    print(f"Metrics: {OUT_METRICS}")
    print("Next: python scripts/evaluate_model.py")
    print("==============================================")


if __name__ == "__main__":
    sys.exit(main())
