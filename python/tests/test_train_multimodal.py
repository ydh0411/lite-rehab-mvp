import csv

from literehab.multimodal import POSE_FEATURE_NAMES
from train_multimodal import IMU_FEATURES, load_recording


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
