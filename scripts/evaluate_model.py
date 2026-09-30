"""
Evaluate the trained YOLOv8 disease model on the validation images.

    python scripts/evaluate_model.py
    python scripts/evaluate_model.py --val datasets/prepared/val --weights app/ai/models/yolov8_disease.pt

Prints and saves (app/ai/models/yolov8_disease_report.json):
  - overall and per-class accuracy (worst classes first)
  - the most common confusions (which disease is mistaken for which)
  - accuracy vs coverage at different confidence thresholds, and the
    CONFIDENCE_THRESHOLD to put in .env for a chosen precision target.
    Below the threshold the app tells the farmer to retake the photo.
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
THRESHOLDS = [0, 50, 60, 70, 80, 85, 90, 95, 98]


def collect_images(val_dir):
    items = []

    for folder in sorted(os.listdir(val_dir)):
        path = os.path.join(val_dir, folder)

        if not os.path.isdir(path):
            continue

        for name in sorted(os.listdir(path)):
            if os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS:
                items.append((os.path.join(path, name), folder))

    return items


def recommend_threshold(rows, precision_target):
    """
    Lowest confidence threshold whose accepted predictions reach the target
    accuracy (so as few photos as possible are rejected).
    """

    for threshold in range(50, 100):
        accepted = [ok for confidence, ok in rows if confidence >= threshold]

        if len(accepted) >= 30 and sum(accepted) / len(accepted) >= precision_target:
            return threshold

    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--val", default="datasets/prepared/val")
    parser.add_argument("--weights", default="app/ai/models/yolov8_disease.pt")
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--precision", type=float, default=0.95, help="accuracy wanted for accepted predictions")
    parser.add_argument("--out", default="app/ai/models/yolov8_disease_report.json")
    args = parser.parse_args()

    from ultralytics import YOLO

    if not os.path.exists(args.weights):
        raise SystemExit(f"Weights not found: {args.weights} (train first)")

    if not os.path.isdir(args.val):
        raise SystemExit(f"Validation folder not found: {args.val} (run scripts/prepare_dataset.py)")

    model = YOLO(args.weights)
    names = model.names

    items = collect_images(args.val)
    print(f"Evaluating {len(items)} images...")

    rows = []                                    # (confidence %, correct)
    per_class = defaultdict(lambda: [0, 0])      # class -> [correct, total]
    confusions = Counter()

    for start in range(0, len(items), args.batch):
        batch = items[start:start + args.batch]

        results = model.predict(
            [path for path, _ in batch], imgsz=args.imgsz, verbose=False
        )

        for (path, actual), result in zip(batch, results):
            predicted = names[int(result.probs.top1)]
            confidence = float(result.probs.top1conf) * 100
            correct = predicted == actual

            rows.append((confidence, correct))
            per_class[actual][1] += 1
            per_class[actual][0] += int(correct)

            if not correct:
                confusions[(actual, predicted)] += 1

        print(f"  {min(start + args.batch, len(items))}/{len(items)}", end="\r")

    total_correct = sum(ok for _, ok in rows)
    accuracy = total_correct / len(rows)

    class_accuracy = {
        name: round(correct / total, 4)
        for name, (correct, total) in per_class.items()
    }
    worst = sorted(class_accuracy.items(), key=lambda item: item[1])[:10]

    coverage = []

    for threshold in THRESHOLDS:
        accepted = [ok for confidence, ok in rows if confidence >= threshold]

        coverage.append({
            "threshold": threshold,
            "accepted_share": round(len(accepted) / len(rows), 4),
            "accuracy_of_accepted": round(sum(accepted) / len(accepted), 4) if accepted else None,
        })

    recommended = recommend_threshold(rows, args.precision)

    report = {
        "images": len(rows),
        "top1_accuracy": round(accuracy, 4),
        "classes": len(per_class),
        "worst_classes": worst,
        "top_confusions": [
            {"actual": a, "predicted": p, "count": n}
            for (a, p), n in confusions.most_common(15)
        ],
        "confidence_table": coverage,
        "precision_target": args.precision,
        "recommended_confidence_threshold": recommended,
        "per_class_accuracy": class_accuracy,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n\n==============================================")
    print(f"Top-1 accuracy: {accuracy * 100:.2f}%  ({total_correct}/{len(rows)})")
    print("\nWeakest classes:")

    for name, value in worst:
        print(f"  {value * 100:5.1f}%  {name}")

    print("\nMost common mistakes (actual -> predicted):")

    for (actual, predicted), count in confusions.most_common(8):
        print(f"  {count:3d}  {actual} -> {predicted}")

    print("\nConfidence threshold   accepted   accuracy of accepted")

    for row in coverage:
        accuracy_text = (
            f"{row['accuracy_of_accepted'] * 100:.1f}%"
            if row["accuracy_of_accepted"] is not None else "-"
        )
        print(f"  >= {row['threshold']:>3}%            {row['accepted_share'] * 100:5.1f}%     {accuracy_text}")

    if recommended:
        print(
            f"\nFor {args.precision * 100:.0f}% accuracy on accepted photos set "
            f"CONFIDENCE_THRESHOLD={recommended} in .env"
        )
    else:
        print(f"\nNo threshold reaches {args.precision * 100:.0f}% accuracy: the model needs more training or data.")

    print(f"\nReport saved: {args.out}")
    print("==============================================")


if __name__ == "__main__":
    main()
