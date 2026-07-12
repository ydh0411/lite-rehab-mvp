import csv
import sys

from literehab.multimodal import POSE_FEATURE_NAMES, load_multimodal_checkpoint
from train_multimodal import IMU_FEATURES, load_recording, main


def test_load_recording_reads_synchronized_schema(tmp_path):
    path = tmp_path / "S01_elbow_ok.csv"
    fields = [*IMU_FEATURES, *POSE_FEATURE_NAMES,
              "subject", "label_exercise", "label_quality"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for _ in range(4):
            row = {name: 0.0 for name in (*IMU_FEATURES, *POSE_FEATURE_NAMES)}
            row.update(subject="S01", label_exercise="elbow_flexion",
                       label_quality="ok")
            writer.writerow(row)

    imu, pose, subject, exercise, quality = load_recording(path)

    assert imu.shape == (4, 6)
    assert pose.shape == (4, len(POSE_FEATURE_NAMES))
    assert (subject, exercise, quality) == ("S01", "elbow_flexion", "ok")


def _write_recording(path, subject, exercise, quality):
    fields = [*IMU_FEATURES, *POSE_FEATURE_NAMES,
              "subject", "label_exercise", "label_quality"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(110):
            row = {name: float(index % 7) for name in IMU_FEATURES}
            row.update({name: float(index % 5) for name in POSE_FEATURE_NAMES})
            row["visibility"] = 0.9
            row["vision_valid"] = 1.0
            row.update(subject=subject, label_exercise=exercise,
                       label_quality=quality)
            writer.writerow(row)


def test_training_cli_saves_a_loadable_checkpoint(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    for subject in ("S01", "S02"):
        _write_recording(data / f"{subject}_idle.csv", subject, "idle", "none")
        _write_recording(data / f"{subject}_elbow.csv", subject,
                         "elbow_flexion", "ok")
    output = tmp_path / "fusion.pt"
    monkeypatch.setattr(sys, "argv", [
        "train_multimodal.py", "--data", str(data),
        "--holdout-subject", "S02", "--epochs", "1",
        "--output", str(output),
    ])

    main()
    checkpoint = load_multimodal_checkpoint(output)

    assert checkpoint.held_out_subject == "S02"
    assert checkpoint.exercise_labels == ("elbow_flexion", "idle")
    assert checkpoint.quality_labels == ("none", "ok")
