import json
import os

import pytest
from PIL import Image

from app.ai.training.prepare import is_good_image, prepare_dataset


def make_images(folder, count, size=(64, 64), start=0):
    os.makedirs(folder, exist_ok=True)

    for i in range(start, start + count):
        Image.new("RGB", size, (i % 255, 100, 50)).save(os.path.join(folder, f"{i}.jpg"))


@pytest.fixture
def raw(tmp_path):
    root = tmp_path / "raw"

    make_images(root / "Tomato___late_blight", 300)     # big class
    make_images(root / "Potato___nematode", 20)         # small class
    make_images(root / "Rose___healthy", 4)             # too small
    (root / "notes.txt").parent.mkdir(exist_ok=True)
    (root / "notes.txt").write_text("not a class folder")

    return str(root)


def count(path):
    return len(os.listdir(path))


def test_big_classes_are_capped_and_small_ones_keep_everything(raw, tmp_path):
    target = str(tmp_path / "prepared")

    report = prepare_dataset(raw, target, max_train=100, max_val=20, log=lambda *a: None)

    tomato = report["classes"]["Tomato___late_blight"]
    assert tomato["train"] == 100 and tomato["val"] == 20

    potato = report["classes"]["Potato___nematode"]
    assert potato["train"] + potato["val"] == 20            # nothing thrown away
    assert potato["val"] == 4                               # 20% of 20

    assert count(os.path.join(target, "train", "Tomato___late_blight")) == 100
    assert count(os.path.join(target, "val", "Tomato___late_blight")) == 20


def test_train_and_val_never_share_an_image(raw, tmp_path):
    target = str(tmp_path / "prepared")

    prepare_dataset(raw, target, max_train=100, max_val=20, log=lambda *a: None)

    for name in ("Tomato___late_blight", "Potato___nematode"):
        train = set(os.listdir(os.path.join(target, "train", name)))
        val = set(os.listdir(os.path.join(target, "val", name)))

        assert train and val
        assert train.isdisjoint(val)


def test_tiny_classes_and_files_are_skipped(raw, tmp_path):
    report = prepare_dataset(raw, str(tmp_path / "p"), min_images=10, log=lambda *a: None)

    assert "Rose___healthy" in report["skipped_classes"]
    assert "Rose___healthy" not in report["classes"]
    assert report["totals"]["classes"] == 2


def test_split_is_reproducible(raw, tmp_path):
    first = str(tmp_path / "a")
    second = str(tmp_path / "b")

    prepare_dataset(raw, first, max_train=50, max_val=10, seed=7, log=lambda *a: None)
    prepare_dataset(raw, second, max_train=50, max_val=10, seed=7, log=lambda *a: None)

    name = "Tomato___late_blight"

    assert sorted(os.listdir(os.path.join(first, "val", name))) == sorted(os.listdir(os.path.join(second, "val", name)))


def test_broken_and_tiny_images_are_skipped(tmp_path):
    root = tmp_path / "raw"
    folder = root / "Tomato___early_blight"
    make_images(folder, 30)

    (folder / "broken.jpg").write_bytes(b"this is not an image")
    make_images(folder, 1, size=(8, 8), start=500)         # tiny image

    report = prepare_dataset(str(root), str(tmp_path / "p"), max_train=100, max_val=100,
                             val_fraction=0.5, log=lambda *a: None)

    prepared = report["classes"]["Tomato___early_blight"]

    assert prepared["train"] + prepared["val"] == 30
    assert prepared["broken_skipped"] == 2

    assert not is_good_image(str(folder / "broken.jpg"))
    assert not is_good_image(str(folder / "500.jpg"))
    assert is_good_image(str(folder / "1.jpg"))


def test_report_file_is_written_and_lists_small_classes(raw, tmp_path):
    target = str(tmp_path / "prepared")

    prepare_dataset(raw, target, max_train=100, max_val=20, log=lambda *a: None)

    with open(os.path.join(target, "dataset_report.json")) as f:
        report = json.load(f)

    assert report["totals"]["train"] == 100 + 16
    assert "Potato___nematode" in report["small_classes_under_100_train_images"]


def test_rerun_replaces_the_previous_output(raw, tmp_path):
    target = str(tmp_path / "prepared")

    prepare_dataset(raw, target, max_train=100, max_val=20, log=lambda *a: None)
    prepare_dataset(raw, target, max_train=10, max_val=5, log=lambda *a: None)

    assert count(os.path.join(target, "train", "Tomato___late_blight")) == 10


def test_missing_or_empty_source_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        prepare_dataset(str(tmp_path / "nope"), str(tmp_path / "t"))

    (tmp_path / "empty").mkdir()

    with pytest.raises(ValueError):
        prepare_dataset(str(tmp_path / "empty"), str(tmp_path / "t"))
