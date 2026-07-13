#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from contextlib import ExitStack
from pathlib import Path


FEATURES = ("ax", "ay", "az", "gx", "gy", "gz")
LABELS = {
    "el-exfl": "elbow_flexion",
    "wr-prsu": "forearm_rotation",
    "sh-exfl": "shoulder_abduction",
}


def convert_public_csv(
    source: Path,
    output: Path,
    target_hz: int = 50,
    max_samples_per_recording: int = 1500,
) -> dict[str, int]:
    """Convert a bounded right-wrist subset of the public Apple Watch CSV."""
    if target_hz <= 0 or max_samples_per_recording <= 0:
        raise ValueError("sample rate and recording limit must be positive")

    output.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    writers: dict[str, csv.DictWriter] = {}
    selected_sessions: dict[tuple[str, str], str] = {}
    with source.open(newline="", encoding="utf-8-sig") as source_handle, ExitStack() as stack:
        reader = csv.DictReader(source_handle)
        for row in reader:
            label = LABELS.get(row.get("MoveType", "").strip())
            if label is None or row.get("Wrist", "").strip() != "rt":
                continue

            source_hz = float(row.get("Hertz", target_hz))
            step = max(1, round(source_hz / target_hz))
            sample_index = int(float(row.get("RecNo", "1"))) - 1
            if sample_index % step:
                continue

            subject = row["UID"].strip()
            session = row["SessionID"].strip().replace("/", "-")
            group = (subject, label)
            selected_sessions.setdefault(group, session)
            if selected_sessions[group] != session:
                continue
            filename = f"{subject}_{label}_{session}_rt.csv"
            if counts.get(filename, 0) >= max_samples_per_recording:
                continue

            if filename not in writers:
                handle = stack.enter_context((output / filename).open("w", newline=""))
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[*FEATURES, "label", "subject"],
                    lineterminator="\n",
                )
                writer.writeheader()
                writers[filename] = writer
                counts[filename] = 0

            radians_to_degrees = 180.0 / math.pi
            writers[filename].writerow({
                "ax": float(row["DMUAccelX"]),
                "ay": float(row["DMUAccelY"]),
                "az": float(row["DMUAccelZ"]),
                "gx": float(row["DMRotX"]) * radians_to_degrees,
                "gy": float(row["DMRotY"]) * radians_to_degrees,
                "gz": float(row["DMRotZ"]) * radians_to_degrees,
                "label": label,
                "subject": subject,
            })
            counts[filename] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare a small right-wrist upper-limb IMU training subset")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/imu_public_small"))
    parser.add_argument("--target-hz", type=int, default=50)
    parser.add_argument("--max-samples", type=int, default=1500)
    args = parser.parse_args()
    counts = convert_public_csv(
        args.source, args.output, args.target_hz, args.max_samples)
    if not counts:
        raise SystemExit("No supported right-wrist recordings found")
    print(f"recordings={len(counts)} samples={sum(counts.values())}")
    for filename, count in sorted(counts.items()):
        print(f"{filename}: {count}")


if __name__ == "__main__":
    main()
