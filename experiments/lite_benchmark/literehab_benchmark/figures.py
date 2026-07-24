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
    "gated_fusion": "Gated Fusion",
    "lite_actionmae": "Lite-ActionMAE (Final)",
}

MODEL_COLORS = {
    "imu_cnn": "#767676",
    "imu_cnn_bigru": PALETTE["teal"],
    "pose_cnn_bigru": PALETTE["red_strong"],
    "early_fusion": PALETTE["green_3"],
    "gated_fusion": PALETTE["violet"],
    "lite_actionmae": PALETTE["blue_main"],
}

MODEL_HATCHES = {
    "imu_cnn": "..",
    "imu_cnn_bigru": "\\\\",
    "pose_cnn_bigru": "xx",
    "early_fusion": "--",
    "gated_fusion": "++",
    "lite_actionmae": "//",
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
        summary: dict[str, object] = {"model": model, "rows": model_rows}
        for name in (
            "accuracy", "macro_f1", "balanced_accuracy", "latency_ms", "parameters"
        ):
            values = np.asarray([row[name] for row in model_rows], dtype=float)
            summary[name] = float(values.mean())
            summary[f"{name}_std"] = float(
                values.std(ddof=1) if len(values) > 1 else 0.0
            )
            summary[f"{name}_values"] = values
        output.append(summary)
    return output


def _seed_payloads(results_dir: Path, stem: str) -> list[dict[str, object]]:
    paths = list(results_dir.glob(f"{stem}_seed*.json"))
    paths.sort(
        key=lambda path: int(path.stem.rsplit("seed", 1)[1])
        if path.stem.rsplit("seed", 1)[1].isdigit()
        else path.name
    )
    if not paths:
        paths = [results_dir / f"{stem}.json"]
    return [json.loads(path.read_text()) for path in paths]


def _score_limits(values: list[float], padding: float = 0.15) -> tuple[float, float]:
    low = min(values)
    high = max(values)
    spread = max(high - low, 0.15)
    return max(0.0, low - max(padding, spread * 0.25)), min(
        100.15, high + max(padding, spread * 0.25)
    )


def _selection_summaries(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Device score using fixed 1 ms/window and 2M-parameter budgets."""
    clean = {row["model"]: row for row in _clean_means(rows)}
    output = []
    for model in MODEL_LABELS:
        if model not in clean:
            continue
        robust_rows = [
            row for row in rows
            if row["model"] == model
            and "_missing_" in str(row["condition"])
            and not str(row["condition"]).endswith("_0.00")
        ]
        grouped: dict[str, list[float]] = {}
        for row in robust_rows:
            grouped.setdefault(str(row["condition"]), []).append(float(row["macro_f1"]))
        condition_means = [float(np.mean(values)) for values in grouped.values()]
        robust_mean = float(np.mean(condition_means)) if condition_means else 0.0
        robust_worst = float(np.min(condition_means)) if condition_means else 0.0
        item = dict(clean[model])
        item["robust_mean"] = robust_mean
        item["robust_worst"] = robust_worst
        output.append(item)

    if not output:
        return output
    for index, item in enumerate(output):
        stability = 1.0 - min(float(item["macro_f1_std"]) / 0.02, 1.0)
        latency_utility = max(0.0, 1.0 - float(item["latency_ms"]) / 1.0)
        parameter_utility = max(0.0, 1.0 - float(item["parameters"]) / 2_000_000)
        item["selection_score"] = (
            0.25 * float(item["macro_f1"])
            + 0.35 * float(item["robust_mean"])
            + 0.20 * float(item["robust_worst"])
            + 0.10 * stability
            + 0.05 * latency_utility
            + 0.05 * parameter_utility
        )
    return output


def _selected_model(rows: list[dict[str, object]]) -> str:
    summaries = _selection_summaries(rows)
    if not summaries:
        raise ValueError("no clean model results found")
    return str(max(summaries, key=lambda item: item["selection_score"])["model"])


def _plot_performance(rows, output_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    means = _clean_means(rows)
    selection = {item["model"]: item for item in _selection_summaries(rows)}
    selected = _selected_model(rows)
    models = [item["model"] for item in means]
    x = np.arange(len(models))
    fig, axes_grid = plt.subplots(2, 2, figsize=(15, 10))
    axes = axes_grid.ravel()
    for axis, metric, title in zip(
        axes[:3],
        ("accuracy", "macro_f1", "balanced_accuracy"),
        ("Accuracy", "Macro-F1", "Balanced accuracy"),
    ):
        values = [100 * float(item[metric]) for item in means]
        errors = [100 * float(item[f"{metric}_std"]) for item in means]
        bars = axis.bar(
            x, values, yerr=errors, capsize=4,
            color=[MODEL_COLORS[model] for model in models],
            edgecolor="black", linewidth=1.1,
        )
        for bar, model in zip(bars, models):
            bar.set_hatch(MODEL_HATCHES[model])
        for index, item in enumerate(means):
            seed_values = 100 * np.asarray(item[f"{metric}_values"])
            jitter = np.linspace(-0.08, 0.08, len(seed_values))
            axis.scatter(index + jitter, seed_values, s=22, c="#272727", zorder=4)
        axis.set_ylim(*_score_limits(values + [
            value + error for value, error in zip(values, errors)
        ]))
        axis.set_title(title, loc="left")
        axis.set_xticks(x, [])
        axis.grid(axis="y", alpha=0.18, linewidth=0.7)
        axis.bar_label(bars, fmt="%.2f", padding=7, fontsize=9)
    axes[0].set_ylabel("Clean test score (%)")

    ordered = sorted(
        selection.values(), key=lambda item: item["selection_score"]
    )
    y = np.arange(len(ordered))
    score_bars = axes[3].barh(
        y, [100 * item["selection_score"] for item in ordered],
        color=[MODEL_COLORS[item["model"]] for item in ordered],
        edgecolor="black", linewidth=1.1,
    )
    for bar, item in zip(score_bars, ordered):
        bar.set_hatch(MODEL_HATCHES[item["model"]])
    axes[3].set_yticks(
        y, [MODEL_LABELS[item["model"]] for item in ordered], fontsize=10
    )
    axes[3].set_xlabel("Pre-registered device score")
    axes[3].set_title("Multi-objective selection", loc="left")
    axes[3].bar_label(score_bars, fmt="%.1f", padding=4, fontsize=9)
    axes[3].grid(axis="x", alpha=0.18, linewidth=0.7)
    fig.suptitle(
        f"Same split, budget and seeds — selected: {MODEL_LABELS[selected]}",
        x=0.01, ha="left", fontweight="bold",
    )
    return finalize_figure(fig, output_dir / "fig_model_performance")


def _plot_efficiency(rows, output_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    means = _selection_summaries(rows)
    selected = _selected_model(rows)
    fig, (axis, table_axis) = plt.subplots(
        1, 2, figsize=(16, 6), gridspec_kw={"width_ratios": [1.25, 1]}
    )
    sizes = [max(90, min(700, row["parameters"] / 500)) for row in means]
    axis.errorbar(
        [row["latency_ms"] for row in means],
        [100 * row["macro_f1"] for row in means],
        xerr=[row["latency_ms_std"] for row in means],
        yerr=[100 * row["macro_f1_std"] for row in means],
        fmt="none", ecolor="#767676", capsize=3, alpha=0.65,
    )
    axis.scatter(
        [row["latency_ms"] for row in means],
        [100 * row["macro_f1"] for row in means],
        s=sizes, c=[MODEL_COLORS[row["model"]] for row in means],
        edgecolor="black", linewidth=1.2, alpha=0.92,
    )
    annotation_offsets = {
        "early_fusion": (8, 10),
        "gated_fusion": (8, -20),
        "lite_actionmae": (8, 10),
    }
    for row in means:
        if row["model"] not in annotation_offsets:
            continue
        axis.annotate(
            MODEL_LABELS[row["model"]],
            (row["latency_ms"], 100 * row["macro_f1"]),
            xytext=annotation_offsets[row["model"]],
            textcoords="offset points", fontsize=9,
            fontweight="bold" if row["model"] == selected else "normal",
        )
    axis.set_xlabel("Inference latency (ms / window)")
    axis.set_ylabel("Clean Macro-F1 (%)")
    axis.set_title("Accuracy–efficiency plane", loc="left")
    axis.grid(alpha=0.18, linewidth=0.7)

    ranked = sorted(means, key=lambda item: item["selection_score"], reverse=True)
    cells = [[
        f"{100 * item['macro_f1']:.2f}",
        f"{100 * item['robust_mean']:.2f}",
        f"{100 * item['robust_worst']:.2f}",
        f"{item['latency_ms']:.3f}",
        f"{int(round(item['parameters'])):,}",
    ] for item in ranked]
    table_axis.set_axis_off()
    table_axis.set_title("Deployment evidence", loc="left", pad=14)
    table = table_axis.table(
        cellText=cells,
        rowLabels=[MODEL_LABELS[item["model"]] for item in ranked],
        colLabels=["Clean", "Robust avg.", "Worst", "ms", "Params"],
        cellLoc="center", rowLoc="left", loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(0.95, 1.45)
    for column in range(5):
        table[(0, column)].set_facecolor(PALETTE["neutral"])
    selected_row = next(
        index + 1 for index, item in enumerate(ranked) if item["model"] == selected
    )
    for column in range(-1, 5):
        table[(selected_row, column)].set_facecolor(PALETTE["green_1"])
    return finalize_figure(fig, output_dir / "fig_efficiency_tradeoff")


def _plot_robustness(rows, output_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    selected_model = _selected_model(rows)
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), sharex=True)
    legend_handles = []
    for column, (prefix, modality_title) in enumerate((
        ("pose_missing_", "Pose/camera corruption"),
        ("imu_missing_", "IMU corruption"),
    )):
        for model in MODEL_LABELS:
            model_rows = [
                row for row in rows
                if row["model"] == model
                and str(row["condition"]).startswith(prefix)
            ]
            if not model_rows:
                continue
            grouped: dict[float, list[float]] = {}
            for row in model_rows:
                rate = float(str(row["condition"]).rsplit("_", 1)[1])
                grouped.setdefault(rate, []).append(100 * float(row["macro_f1"]))
            rates = np.asarray(sorted(grouped))
            values = np.asarray([np.mean(grouped[rate]) for rate in rates])
            errors = np.asarray([
                np.std(grouped[rate], ddof=1) if len(grouped[rate]) > 1 else 0.0
                for rate in rates
            ])
            clean = values[0] if 0 in rates else values.max()
            style = {
                "linewidth": 3.2 if model == selected_model else 1.6,
                "alpha": 1.0 if model == selected_model else 0.72,
                "zorder": 4 if model == selected_model else 2,
            }
            line = axes[0, column].plot(
                rates * 100, values, marker="o", markersize=5,
                color=MODEL_COLORS[model], label=MODEL_LABELS[model], **style,
            )[0]
            axes[0, column].fill_between(
                rates * 100, values - errors, values + errors,
                color=MODEL_COLORS[model], alpha=0.10,
            )
            axes[1, column].plot(
                rates * 100, values - clean, marker="o", markersize=5,
                color=MODEL_COLORS[model], **style,
            )
            if column == 0:
                legend_handles.append(line)
        axes[0, column].set_title(modality_title, loc="left")
        axes[1, column].axhline(0, color="#767676", linewidth=1)
        axes[1, column].set_xlabel("Missing temporal samples (%)")
        for axis in axes[:, column]:
            axis.grid(alpha=0.18, linewidth=0.7)
    axes[0, 0].set_ylabel("Macro-F1 (%)")
    axes[1, 0].set_ylabel("Change from clean (percentage points)")
    axes[0, 1].legend(
        handles=legend_handles, ncols=2, fontsize=9, loc="lower left"
    )
    fig.suptitle(
        f"Robustness across all models and seeds — highlighted: "
        f"{MODEL_LABELS[selected_model]}",
        x=0.01, ha="left", fontweight="bold",
    )
    return finalize_figure(fig, output_dir / "fig_robustness")


def _plot_confusion(rows, results_dir: Path, output_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    selected = _selected_model(rows)
    payloads = _seed_payloads(results_dir, f"confusion_{selected}")
    payload = payloads[0]
    matrix = np.sum(
        [np.asarray(item["matrix"], dtype=float) for item in payloads], axis=0
    )
    row_sum = matrix.sum(axis=1, keepdims=True)
    normalized = np.divide(matrix, row_sum, out=np.zeros_like(matrix), where=row_sum != 0)
    fig, (ax, class_axis) = plt.subplots(
        1, 2, figsize=(16, 7), gridspec_kw={"width_ratios": [1.25, 0.9]}
    )
    image = ax.imshow(normalized, cmap="Blues", vmin=0, vmax=1)
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            if row == column or matrix[row, column] > 0:
                label = (
                    f"{100 * normalized[row, column]:.1f}%"
                    if row == column else f"{int(matrix[row, column])}"
                )
                ax.text(
                    column, row, label, ha="center", va="center",
                    color="white" if normalized[row, column] > 0.55 else "#272727",
                    fontsize=7 if matrix.shape[0] > 6 else 10,
                )
    labels = payload["class_names"]
    ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("Actual class")
    ax.set_title(f"{MODEL_LABELS[selected]}: aggregate confusion", loc="left")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="Row-normalized rate")

    recall = np.diag(normalized) * 100
    support = matrix.sum(axis=1)
    y = np.arange(len(labels))
    support_axis = class_axis.twiny()
    support_axis.barh(y, support, color=PALETTE["neutral"], alpha=0.5)
    class_axis.scatter(recall, y, color=PALETTE["blue_main"], s=45, zorder=3)
    class_axis.set_yticks(y, labels)
    class_axis.invert_yaxis()
    class_axis.set_xlim(max(0, recall.min() - 3), 100.2)
    class_axis.set_xlabel("Per-class recall (%)")
    support_axis.set_xlabel("Test support across seeds")
    class_axis.set_title("Class-level reliability", loc="left")
    class_axis.grid(axis="x", alpha=0.18, linewidth=0.7)
    for value, row_index in zip(recall, y):
        class_axis.text(value - 0.15, row_index, f"{value:.1f}", ha="right", va="center", fontsize=8)
    return finalize_figure(fig, output_dir / "fig_confusion_matrix")


def _plot_history(rows, results_dir: Path, output_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    ranked = sorted(
        _selection_summaries(rows),
        key=lambda item: item["selection_score"],
        reverse=True,
    )
    models = [item["model"] for item in ranked[:2]]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    for model in models:
        payloads = _seed_payloads(results_dir, f"history_{model}")
        epochs = np.asarray(payloads[0]["epoch"])
        losses = np.asarray([item["train_loss"] for item in payloads], dtype=float)
        scores = 100 * np.asarray(
            [item["test_macro_f1"] for item in payloads], dtype=float
        )
        for axis, values, label in (
            (axes[0], losses, MODEL_LABELS[model]),
            (axes[1], scores, MODEL_LABELS[model]),
        ):
            mean = values.mean(axis=0)
            std = values.std(axis=0, ddof=1) if len(values) > 1 else np.zeros_like(mean)
            axis.plot(
                epochs, mean, marker="o", linewidth=2.6,
                color=MODEL_COLORS[model], label=label,
            )
            axis.fill_between(
                epochs, mean - std, mean + std,
                color=MODEL_COLORS[model], alpha=0.16,
            )
    axes[0].set_ylabel("Training objective")
    axes[1].set_ylabel("Test Macro-F1 (%)")
    for axis, title in zip(axes, ("Optimization", "Generalization")):
        axis.set_xlabel("Epoch")
        axis.set_title(title, loc="left")
        axis.grid(alpha=0.18, linewidth=0.7)
    axes[1].legend(loc="lower right", fontsize=10)
    fig.suptitle(
        "Top two deployment candidates: mean ± SD across seeds",
        x=0.01, ha="left", fontweight="bold",
    )
    fig.text(
        0.01, 0.005,
        "Training objectives differ: Lite-ActionMAE = classification + token "
        "reconstruction; Gated Fusion = classification only.",
        fontsize=9, color="#4D4D4D",
    )
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
    outputs.extend(_plot_confusion(rows, results_dir, output_dir))
    outputs.extend(_plot_history(rows, results_dir, output_dir))
    return outputs
