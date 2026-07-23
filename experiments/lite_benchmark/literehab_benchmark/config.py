from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path


MODEL_NAMES = (
    "imu_cnn",
    "imu_cnn_bigru",
    "pose_cnn_bigru",
    "early_fusion",
    "gated_fusion",
    "lite_actionmae",
)


@dataclass(frozen=True)
class BenchmarkConfig:
    models: tuple[str, ...] = MODEL_NAMES
    epochs: int = 8
    seeds: tuple[int, ...] = (7,)
    batch_size: int = 64
    learning_rate: float = 1e-3
    max_train_windows: int = 5000
    max_test_windows: int = 2000
    mixed_precision: bool = True
    num_workers: int = 2
    robustness_missing_rates: tuple[float, ...] = (0.0, 0.25, 0.5)
    warmup_batches: int = 10
    latency_batches: int = 40

    def validate(self) -> "BenchmarkConfig":
        unknown = sorted(set(self.models) - set(MODEL_NAMES))
        if unknown:
            raise ValueError(f"unknown benchmark model: {', '.join(unknown)}")
        if self.epochs <= 0:
            raise ValueError("epochs must be positive")
        if not self.seeds:
            raise ValueError("at least one seed is required")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if self.max_train_windows <= 0 or self.max_test_windows <= 0:
            raise ValueError("window budgets must be positive")
        if any(rate < 0 or rate > 1 for rate in self.robustness_missing_rates):
            raise ValueError("missing rates must be between zero and one")
        return self

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["models"] = list(self.models)
        value["seeds"] = list(self.seeds)
        value["robustness_missing_rates"] = list(self.robustness_missing_rates)
        return value


def load_config(path: str | Path) -> BenchmarkConfig:
    raw = json.loads(Path(path).read_text())
    allowed = {item.name for item in fields(BenchmarkConfig)}
    extra = sorted(set(raw) - allowed)
    if extra:
        raise ValueError(f"unknown config keys: {', '.join(extra)}")
    for name in ("models", "seeds", "robustness_missing_rates"):
        if name in raw:
            raw[name] = tuple(raw[name])
    return BenchmarkConfig(**raw).validate()
