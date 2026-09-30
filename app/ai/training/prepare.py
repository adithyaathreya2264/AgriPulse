"""
Prepare a class-folder image dataset for YOLOv8 classification training.

    source/                         target/
      Tomato___late_blight/*.jpg      train/Tomato___late_blight/*.jpg
      Rose___healthy/*.jpg            val/Tomato___late_blight/*.jpg
      ...                             dataset_report.json

- checks every selected image (readable, not tiny) and skips broken ones
- balances the classes: at most `max_train` training images per class, so a
  class with 13,000 photos does not drown one with 70 (and CPU training
  stays affordable). Small classes keep everything.
- the split is reproducible (fixed seed) and images are hard-linked, not
  copied, when possible (no extra disk space).
"""

import json
import os
import random
import shutil

from PIL import Image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MIN_SIDE_PIXELS = 32


def is_good_image(path):
    """Readable image that is not tiny."""

    try:
        with Image.open(path) as image:
            image.verify()

        with Image.open(path) as image:
            width, height = image.size

        return min(width, height) >= MIN_SIDE_PIXELS

    except Exception:
        return False


def link_or_copy(source, target):
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def list_classes(source):
    return sorted(
        name for name in os.listdir(source)
        if os.path.isdir(os.path.join(source, name))
    )


def list_images(folder):
    with os.scandir(folder) as entries:
        return sorted(
            entry.name for entry in entries
            if entry.is_file()
            and os.path.splitext(entry.name)[1].lower() in IMAGE_EXTENSIONS
        )


def prepare_dataset(
    source,
    target,
    max_train=500,
    max_val=100,
    val_fraction=0.2,
    seed=0,
    min_images=10,
    check_images=True,
    clean=True,
    log=print
):
    """
    Returns the report dict (also written to target/dataset_report.json).
    """

    if not os.path.isdir(source):
        raise FileNotFoundError(f"Dataset folder not found: {source}")

    classes = list_classes(source)

    if not classes:
        raise ValueError(f"No class folders found in {source}")

    if clean and os.path.isdir(target):
        shutil.rmtree(target)

    rng = random.Random(seed)

    report = {
        "source": os.path.abspath(source),
        "settings": {
            "max_train_per_class": max_train,
            "max_val_per_class": max_val,
            "val_fraction": val_fraction,
            "seed": seed,
        },
        "classes": {},
        "skipped_classes": {},
    }

    totals = {"train": 0, "val": 0, "available": 0, "broken": 0}

    for index, name in enumerate(classes, start=1):
        folder = os.path.join(source, name)
        images = list_images(folder)

        if len(images) < min_images:
            report["skipped_classes"][name] = (
                f"only {len(images)} images (needs at least {min_images})"
            )
            log(f"[{index}/{len(classes)}] {name}: skipped ({len(images)} images)")
            continue

        rng.shuffle(images)

        val_count = min(max_val, max(2, round(len(images) * val_fraction)))

        train, val, broken = [], [], 0
        wanted = {"val": val_count, "train": max_train}

        # Take images in shuffled order until both parts are full, skipping
        # broken files (only the images we would use are checked)
        for image in images:
            part = "val" if len(val) < wanted["val"] else "train"

            if part == "train" and len(train) >= wanted["train"]:
                break

            path = os.path.join(folder, image)

            if check_images and not is_good_image(path):
                broken += 1
                continue

            (val if part == "val" else train).append(image)

        if not train or not val:
            report["skipped_classes"][name] = "not enough valid images"
            log(f"[{index}/{len(classes)}] {name}: skipped (not enough valid images)")
            continue

        for part, files in (("train", train), ("val", val)):
            destination = os.path.join(target, part, name)
            os.makedirs(destination, exist_ok=True)

            for image in files:
                link_or_copy(
                    os.path.join(folder, image),
                    os.path.join(destination, image)
                )

        report["classes"][name] = {
            "available": len(images),
            "train": len(train),
            "val": len(val),
            "broken_skipped": broken,
        }

        totals["train"] += len(train)
        totals["val"] += len(val)
        totals["available"] += len(images)
        totals["broken"] += broken

        log(
            f"[{index}/{len(classes)}] {name}: "
            f"train {len(train)} | val {len(val)} (of {len(images)})"
        )

    report["totals"] = {**totals, "classes": len(report["classes"])}

    small = [
        name for name, info in report["classes"].items()
        if info["train"] < 100
    ]
    report["small_classes_under_100_train_images"] = small

    os.makedirs(target, exist_ok=True)

    with open(os.path.join(target, "dataset_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report
