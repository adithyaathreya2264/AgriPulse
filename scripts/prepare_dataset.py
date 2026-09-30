"""
Prepare the leaf-disease dataset for training (balanced train/val split).

    python scripts/prepare_dataset.py
    python scripts/prepare_dataset.py --max-train 800 --max-val 150
    python scripts/prepare_dataset.py --source datasets/other --target datasets/other_prepared

Output: datasets/prepared/train, datasets/prepared/val, dataset_report.json
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.training.prepare import prepare_dataset  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default="datasets/leaf_disease_detection_dataset")
    parser.add_argument("--target", default="datasets/prepared")
    parser.add_argument("--max-train", type=int, default=500, help="training images per class (cap)")
    parser.add_argument("--max-val", type=int, default=100, help="validation images per class (cap)")
    parser.add_argument("--val-fraction", type=float, default=0.2, help="validation share for small classes")
    parser.add_argument("--min-images", type=int, default=10, help="skip classes with fewer images")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-check", action="store_true", help="do not verify that images open")
    args = parser.parse_args()

    report = prepare_dataset(
        args.source,
        args.target,
        max_train=args.max_train,
        max_val=args.max_val,
        val_fraction=args.val_fraction,
        min_images=args.min_images,
        seed=args.seed,
        check_images=not args.no_check,
    )

    totals = report["totals"]

    print("\n==============================================")
    print(f"Classes: {totals['classes']}   Train: {totals['train']}   Val: {totals['val']}")
    print(f"Available images: {totals['available']}   Broken skipped: {totals['broken']}")

    if report["skipped_classes"]:
        print("Skipped classes:", report["skipped_classes"])

    if report["small_classes_under_100_train_images"]:
        print(
            "Small classes (< 100 training images, expect lower accuracy):",
            ", ".join(report["small_classes_under_100_train_images"])
        )

    print(f"Report: {os.path.join(args.target, 'dataset_report.json')}")
    print("==============================================")


if __name__ == "__main__":
    main()
