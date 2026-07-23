from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path

import numpy as np


PALETTE = {
    "blue_main": "#0F4D92",
    "blue_secondary": "#3775BA",
    "green_1": "#DDF3DE",
    "green_2": "#AADCA9",
    "green_3": "#8BCF8B",
    "red_1": "#F6CFCB",
    "red_2": "#E9A6A1",
    "red_strong": "#B64342",
    "neutral": "#CFCECE",
    "highlight": "#FFD700",
    "teal": "#42949E",
    "violet": "#9A4D8E",
}

MODEL_LABELS = {
    "imu_cnn": "IMU CNN",
    "imu_cnn_bigru": "IMU CNN-BiGRU",
    "pose_cnn_bigru": "Pose CNN-BiGRU",
    "early_fusion": "Early Fusion",
    "gated_fusion": "Gated Fusion (Ours)",
}


@dataclass(frozen=True)
class FigureStyle:
    font_size: int = 16
    axes_linewidth: float = 2.5
    font_family: tuple[str, ...] = ("Arial", "Helvetica", "DejaVu Sans", "sans-serif")


def apply_publication_style(style: FigureStyle | None = None) -> None:
    import matplotlib.pyplot as plt

    style = style or FigureStyle()
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": list(style.font_family),
        "font.size": style.font_size,
        "axes.linewidth": style.axes_linewidth,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "legend.frameon": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    })


def finalize_figure(fig, out_path: str | Path, dpi: int = 300) -> list[Path]:
    import matplotlib.pyplot as plt

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=1.5)
    outputs = []
    for suffix in (".png", ".pdf"):
        target = out_path.with_suffix(suffix)
        fig.savefig(target, dpi=dpi, bbox_inches="tight", pad_inches=0.06)
        outputs.append(target)
    plt.close(fig)
    return outputs


def expected_figure_stems() -> tuple[str, ...]:
    return (
        "fig_model_performance",
        "fig_efficiency_tradeoff",
        "fig_robustness",
        "fig_confusion_matrix",
        "fig_training_curves",
    )


def _load_rows(path: Path) -> list[dict[str, object]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    numeric = (
        "accuracy", "macro_f1", "balanced_accuracy", "latency_ms", "parameters", "seed"
    )
    for row in rows:
        for name in numeric:
            row[name] = float(row[name])
    return rows


def _clean_means(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    clean = [row for row in rows if row["condition"] == "clean"]
    output = []
    for model in MODEL_LABELS:
        model_rows = [row for row in clean if row["model"] == model]
        if not model_rows:
            continue
        output.append({
            "model": model,
            **{
                name: float(np.mean([row[name] for row in model_rows]))
                for name in ("accuracy", "macro_f1", "balanced_accuracy", "latency_ms", "parameters")
            },
        })
    return output


def _plot_performance(rows, output_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    means = _clean_means(rows)
    labels = [MODEL_LABELS[row["model"]] for row in means]
    x = np.arange(len(means))
    width = 0.36
    fig, ax = plt.subplots(figsize=(12, 6))
    accuracy = [100 * row["accuracy"] for row in means]
    macro_f1 = [100 * row["macro_f1"] for row in means]
    bars_a = ax.bar(
        x - width / 2, accuracy, width, label="Accuracy", color=PALETTE["green_3"],
        edgecolor="black", linewidth=1.3,
    )
    bars_f = ax.bar(
        x + width / 2, macro_f1, width, label="Macro-F1", color=PALETTE["blue_main"],
        edgecolor="black", linewidth=1.3, hatch="//",
    )
    ax.set_xticks(x, labels, rotation=12, ha="right")
    ax.set_ylabel("Score (%)")
    ax.set_title("LiteRehab action-recognition benchmark", loc="left", pad=18)
    ax.legend(ncols=2, loc="upper right", bbox_to_anchor=(1.0, 1.10), fontsize=12)
    low = min(accuracy + macro_f1)
    high = max(accuracy + macro_f1)
    ax.set_ylim(max(0, low - 10), max(105, high + 10))
    ax.bar_label(bars_a, fmt="%.1f", padding=3, fontsize=10)
    ax.bar_label(bars_f, fmt="%.1f", padding=3, fontsize=10)
    return finalize_figure(fig, output_dir / "fig_model_performance")


def _plot_efficiency(rows, output_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    means = _clean_means(rows)
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = [
        PALETTE["blue_main"] if row["model"] == "gated_fusion" else PALETTE["neutral"]
        for row in means
    ]
    sizes = [max(90, min(700, row["parameters"] / 500)) for row in means]
    ax.scatter(
        [row["latency_ms"] for row in means],
        [100 * row["macro_f1"] for row in means],
        s=sizes, c=colors, edgecolor="black", linewidth=1.2, alpha=0.9,
    )
    for row in means:
        ax.annotate(
            MODEL_LABELS[row["model"]],
            (row["latency_ms"], 100 * row["macro_f1"]),
            xytext=(6, 7), textcoords="offset points", fontsize=10,
        )
    ax.set_xlabel("Inference latency (ms / window)")
    ax.set_ylabel("Macro-F1 (%)")
    ax.set_title("Accuracy–efficiency trade-off")
    return finalize_figure(fig, output_dir / "fig_efficiency_tradeoff")


def _plot_robustness(rows, output_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    gated = [row for row in rows if row["model"] == "gated_fusion"]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for prefix, label, color, marker in (
        ("pose_missing_", "Missing pose", PALETTE["red_strong"], "o"),
        ("imu_missing_", "Missing IMU", PALETTE["teal"], "s"),
    ):
        selected = [row for row in gated if str(row["condition"]).startswith(prefix)]
        if not selected:
            if prefix == "imu_missing_":
                selected = [row for row in gated if str(row["condition"]).startswith("pose_missing_")]
                label = "Missing modality"
        selected.sort(key=lambda row: float(str(row["condition"]).rsplit("_", 1)[1]))
        if selected:
            rates = [100 * float(str(row["condition"]).rsplit("_", 1)[1]) for row in selected]
            values = [100 * row["macro_f1"] for row in selected]
            ax.plot(rates, values, marker=marker, linewidth=2.5, color=color, label=label)
    ax.set_xlabel("Missing samples (%)")
    ax.set_ylabel("Macro-F1 (%)")
    ax.set_title("Robustness to missing modalities")
    ax.legend()
    return finalize_figure(fig, output_dir / "fig_robustness")


def _plot_confusion(results_dir: Path, output_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    payload = json.loads((results_dir / "confusion_gated_fusion.json").read_text())
    matrix = np.asarray(payload["matrix"], dtype=float)
    row_sum = matrix.sum(axis=1, keepdims=True)
    normalized = np.divide(matrix, row_sum, out=np.zeros_like(matrix), where=row_sum != 0)
    fig, ax = plt.subplots(figsize=(7, 6))
    image = ax.imshow(normalized, cmap="Blues", vmin=0, vmax=1)
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            ax.text(
                column, row, f"{normalized[row, column] * 100:.0f}%\n(n={int(matrix[row, column])})",
                ha="center", va="center",
                color="white" if normalized[row, column] > 0.55 else "#272727", fontsize=11,
            )
    labels = payload["class_names"]
    ax.set_xticks(range(len(labels)), labels, rotation=20, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("Actual class")
    ax.set_title("Gated-fusion confusion matrix")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="Row-normalized rate")
    return finalize_figure(fig, output_dir / "fig_confusion_matrix")


def _plot_history(results_dir: Path, output_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    payload = json.loads((results_dir / "history_gated_fusion.json").read_text())
    fig, loss_axis = plt.subplots(figsize=(8.5, 5.5))
    score_axis = loss_axis.twinx()
    loss_axis.plot(
        payload["epoch"], payload["train_loss"], color=PALETTE["red_strong"],
        marker="o", linewidth=2.5, label="Training loss",
    )
    score_axis.plot(
        payload["epoch"], np.asarray(payload["test_macro_f1"]) * 100,
        color=PALETTE["blue_main"], marker="s", linewidth=2.5, label="Test Macro-F1",
    )
    loss_axis.set_xlabel("Epoch")
    loss_axis.set_ylabel("Cross-entropy loss", color=PALETTE["red_strong"])
    score_axis.set_ylabel("Macro-F1 (%)", color=PALETTE["blue_main"])
    loss_axis.set_title("Lightweight training convergence")
    lines = loss_axis.lines + score_axis.lines
    loss_axis.legend(lines, [line.get_label() for line in lines], loc="center right")
    return finalize_figure(fig, output_dir / "fig_training_curves")


def generate_figures(results_dir: str | Path, output_dir: str | Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg", force=True)
    results_dir = Path(results_dir)
    output_dir = Path(output_dir)
    apply_publication_style()
    rows = _load_rows(results_dir / "summary.csv")
    outputs = []
    outputs.extend(_plot_performance(rows, output_dir))
    outputs.extend(_plot_efficiency(rows, output_dir))
    outputs.extend(_plot_robustness(rows, output_dir))
    outputs.extend(_plot_confusion(results_dir, output_dir))
    outputs.extend(_plot_history(results_dir, output_dir))
    return outputs
