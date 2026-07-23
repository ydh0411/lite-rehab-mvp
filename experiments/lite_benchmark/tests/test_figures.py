import csv
import json
from pathlib import Path

from literehab_benchmark.figures import expected_figure_stems, generate_figures


def test_figure_suite_exports_ppt_png_and_vector_pdf(tmp_path: Path):
    results = tmp_path / "results"
    results.mkdir()
    rows = []
    for index, name in enumerate((
        "imu_cnn", "imu_cnn_bigru", "pose_cnn_bigru", "early_fusion", "gated_fusion"
    )):
        rows.append({
            "model": name,
            "condition": "clean",
            "accuracy": 0.65 + index * 0.03,
            "macro_f1": 0.63 + index * 0.03,
            "balanced_accuracy": 0.62 + index * 0.03,
            "latency_ms": 1.0 + index,
            "parameters": 10000 * (index + 1),
            "seed": 7,
        })
    for missing_rate in (0.0, 0.25, 0.5):
        rows.append({
            "model": "gated_fusion",
            "condition": f"pose_missing_{missing_rate:.2f}",
            "accuracy": 0.78 - missing_rate * 0.1,
            "macro_f1": 0.77 - missing_rate * 0.1,
            "balanced_accuracy": 0.76 - missing_rate * 0.1,
            "latency_ms": 4.0,
            "parameters": 50000,
            "seed": 7,
        })
    with (results / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    (results / "confusion_gated_fusion.json").write_text(json.dumps({
        "class_names": ["elbow", "shoulder"],
        "matrix": [[8, 2], [1, 9]],
    }))
    (results / "history_gated_fusion.json").write_text(json.dumps({
        "epoch": [1, 2, 3],
        "train_loss": [1.0, 0.7, 0.5],
        "test_macro_f1": [0.5, 0.65, 0.75],
    }))

    outputs = generate_figures(results, tmp_path / "figures")

    for stem in expected_figure_stems():
        assert (tmp_path / "figures" / f"{stem}.png") in outputs
        assert (tmp_path / "figures" / f"{stem}.pdf") in outputs
        assert (tmp_path / "figures" / f"{stem}.png").stat().st_size > 0
