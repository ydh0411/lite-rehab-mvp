import csv
import json
from pathlib import Path

import matplotlib.image as mpimg

from literehab_benchmark.figures import expected_figure_stems, generate_figures


def test_figure_suite_exports_ppt_png_and_vector_pdf(tmp_path: Path):
    results = tmp_path / "results"
    results.mkdir()
    rows = []
    for seed_index, seed in enumerate((7, 17, 27)):
        model_names = (
            "imu_cnn", "imu_cnn_bigru", "pose_cnn_bigru", "early_fusion",
            "gated_fusion", "lite_actionmae",
        )
        for index, name in enumerate(model_names):
            rows.append({
                "model": name,
                "condition": "clean",
                "accuracy": 0.65 + index * 0.03 + seed_index * 0.002,
                "macro_f1": 0.63 + index * 0.03 + seed_index * 0.002,
                "balanced_accuracy": 0.62 + index * 0.03 + seed_index * 0.002,
                "latency_ms": 1.0 + index + seed_index * 0.1,
                "parameters": 10000 * (index + 1),
                "seed": seed,
            })
        for model_index, name in enumerate(model_names):
            for missing_rate in (0.0, 0.25, 0.5):
                for prefix, penalty in (("pose", 0.10), ("imu", 0.16)):
                    robust_bonus = 0.03 if name == "lite_actionmae" else 0.0
                    rows.append({
                        "model": name,
                        "condition": f"{prefix}_missing_{missing_rate:.2f}",
                        "accuracy": 0.68 + model_index * 0.02 + robust_bonus
                        - missing_rate * penalty + seed_index * 0.002,
                        "macro_f1": 0.67 + model_index * 0.02 + robust_bonus
                        - missing_rate * penalty + seed_index * 0.002,
                        "balanced_accuracy": 0.66 + model_index * 0.02 + robust_bonus
                        - missing_rate * penalty + seed_index * 0.002,
                        "latency_ms": 1.0 + model_index + seed_index * 0.1,
                        "parameters": 10000 * (model_index + 1),
                        "seed": seed,
                    })
    with (results / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    for seed_index, seed in enumerate((7, 17, 27)):
        confusion = {
            "class_names": ["elbow", "shoulder"],
            "matrix": [[8 + seed_index, 2], [1, 9 + seed_index]],
        }
        history = {
            "epoch": [1, 2, 3],
            "train_loss": [1.0, 0.7, 0.5 - seed_index * 0.02],
            "test_macro_f1": [0.5, 0.65, 0.75 + seed_index * 0.01],
        }
        for name in model_names:
            (results / f"confusion_{name}_seed{seed}.json").write_text(
                json.dumps(confusion)
            )
            (results / f"history_{name}_seed{seed}.json").write_text(
                json.dumps(history)
            )
    for name in model_names:
        (results / f"confusion_{name}.json").write_text(json.dumps(confusion))
        (results / f"history_{name}.json").write_text(json.dumps(history))

    outputs = generate_figures(results, tmp_path / "figures")

    for stem in expected_figure_stems():
        assert (tmp_path / "figures" / f"{stem}.png") in outputs
        assert (tmp_path / "figures" / f"{stem}.pdf") in outputs
        assert (tmp_path / "figures" / f"{stem}.png").stat().st_size > 0

    performance = mpimg.imread(tmp_path / "figures" / "fig_model_performance.png")
    robustness = mpimg.imread(tmp_path / "figures" / "fig_robustness.png")
    assert performance.shape[1] > performance.shape[0]
    assert robustness.shape[1] > robustness.shape[0]
