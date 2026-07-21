import json
from pathlib import Path

import numpy as np

from literehab_benchmark.prepare_mri import prepare_mri_windows


def test_prepare_mri_uses_precomputed_pose_and_action_segments(tmp_path: Path):
    feature_dir = tmp_path / "pose_features"
    feature_dir.mkdir()
    time_steps = 80
    rgb = np.arange(time_steps * 17 * 3, dtype=np.float32).reshape(time_steps, 17, 3)
    imu = rgb + 100
    np.savez(feature_dir / "subject01.npz", rgb=rgb, imu=imu)
    annotation = tmp_path / "split.json"
    annotation.write_text(json.dumps({
        "database": {
            "subject01": {
                "subset": "training",
                "fps": 10,
                "annotations": [
                    {"label": "elbow_flexion", "label_id": 0, "segment": [1.0, 5.0]},
                    {"label": "shoulder_abduction", "label_id": 1, "segment": [5.0, 8.0]},
                ],
            }
        }
    }))
    output = tmp_path / "benchmark.npz"

    count = prepare_mri_windows(
        feature_dir=feature_dir,
        annotation_path=annotation,
        output_path=output,
        window_size=20,
        stride=20,
        selected_labels=("elbow_flexion", "shoulder_abduction"),
    )

    assert count == 3
    with np.load(output) as data:
        assert data["imu"].shape == (3, 51, 20)
        assert data["pose"].shape == (3, 51, 20)
        assert data["labels"].tolist() == [0, 0, 1]
        assert data["subjects"].tolist() == ["subject01"] * 3
        assert data["class_names"].tolist() == ["elbow_flexion", "shoulder_abduction"]
