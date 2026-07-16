from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SAFE_SESSION_ID = re.compile(r"[A-Za-z0-9_.-]+")
SUPPORTED_ROM_STATES = {
    "elbow_flexion": "elbow_angle_deg",
    "shoulder_abduction": "shoulder_angle_deg",
}


@dataclass(frozen=True)
class SeriesPoint:
    t_s: float
    value: float


@dataclass(frozen=True)
class SessionSummary:
    session_id: str
    subject: str
    started_at: str
    duration_s: float | None
    repetitions: int
    exercises: tuple[str, ...]
    good_form_percent: float | None
    max_rom_deg: float | None
    serial_completeness_percent: float
    pose_completeness_percent: float
    ecg_completeness_percent: float | None
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class SessionReport:
    session_id: str
    subject: str
    started_at: str
    duration_s: float | None
    repetitions: int
    exercises: tuple[str, ...]
    quality_counts: dict[str, int]
    good_form_percent: float | None
    max_rom_deg: float | None
    average_bpm: float | None
    serial_completeness_percent: float
    pose_completeness_percent: float
    ecg_completeness_percent: float | None
    warnings: tuple[str, ...]
    repetition_series: tuple[SeriesPoint, ...]
    rom_series: tuple[SeriesPoint, ...]
    bpm_series: tuple[SeriesPoint, ...]

    def to_summary(self) -> SessionSummary:
        return SessionSummary(
            session_id=self.session_id,
            subject=self.subject,
            started_at=self.started_at,
            duration_s=self.duration_s,
            repetitions=self.repetitions,
            exercises=self.exercises,
            good_form_percent=self.good_form_percent,
            max_rom_deg=self.max_rom_deg,
            serial_completeness_percent=self.serial_completeness_percent,
            pose_completeness_percent=self.pose_completeness_percent,
            ecg_completeness_percent=self.ecg_completeness_percent,
            warnings=self.warnings,
        )


def _number(row: dict[str, str], key: str) -> float:
    return float(row[key])


def _truthy(value: str) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return value.strip().lower() in {"true", "yes", "connected"}


class SessionRepository:
    def __init__(self, root: Path):
        self.root = Path(root)

    def list_sessions(self) -> list[SessionSummary]:
        reports = [self._parse(path) for path in self._session_paths()]
        reports.sort(key=lambda item: item.started_at, reverse=True)
        return [report.to_summary() for report in reports]

    def get_report(self, session_id: str) -> SessionReport:
        if SAFE_SESSION_ID.fullmatch(session_id) is None:
            raise KeyError(session_id)
        path = self.root / f"{session_id}.csv"
        if not path.is_file() or path.name.endswith("_ecg.csv"):
            raise KeyError(session_id)
        return self._parse(path)

    def _session_paths(self) -> list[Path]:
        if not self.root.is_dir():
            return []
        return sorted(
            path
            for path in self.root.glob("*.csv")
            if not path.name.endswith("_ecg.csv")
        )

    def _parse(self, path: Path) -> SessionReport:
        warnings: list[str] = []
        rows, total_rows, invalid_rows = self._read_session_rows(path)
        if invalid_rows:
            warnings.append(f"{invalid_rows} session rows could not be parsed")
        if not rows:
            warnings.append("No valid serial samples")

        times = [row["received_s"] for row in rows]
        first_time = min(times) if times else 0.0
        duration_s = round(max(times) - first_time, 3) if times else None
        subject = next(
            (str(row["subject"]) for row in rows if row["subject"]),
            "Unassigned",
        )
        exercises = tuple(sorted({
            str(row["state"])
            for row in rows
            if row["state"] != "idle"
        }))

        repetitions, repetition_series = self._repetitions(rows, first_time)
        quality_counts = self._quality_counts(rows)
        quality_total = sum(quality_counts.values())
        good_form_percent = (
            round(100.0 * quality_counts.get("ok", 0) / quality_total, 1)
            if quality_total
            else None
        )
        max_rom_deg, rom_series = self._rom(rows, first_time)

        valid_pose = sum(bool(row["vision_valid"]) for row in rows)
        pose_completeness = (
            round(100.0 * valid_pose / len(rows), 1) if rows else 0.0
        )
        if valid_pose == 0:
            warnings.append("No valid pose samples")

        ecg_path = path.with_name(f"{path.stem}_ecg{path.suffix}")
        average_bpm, ecg_completeness, bpm_series, ecg_warning = (
            self._read_ecg(ecg_path)
        )
        if ecg_warning:
            warnings.append(ecg_warning)

        serial_completeness = (
            round(100.0 * len(rows) / total_rows, 1) if total_rows else 0.0
        )
        started_at = datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).isoformat()

        return SessionReport(
            session_id=path.stem,
            subject=subject,
            started_at=started_at,
            duration_s=duration_s,
            repetitions=repetitions,
            exercises=exercises,
            quality_counts=quality_counts,
            good_form_percent=good_form_percent,
            max_rom_deg=max_rom_deg,
            average_bpm=average_bpm,
            serial_completeness_percent=serial_completeness,
            pose_completeness_percent=pose_completeness,
            ecg_completeness_percent=ecg_completeness,
            warnings=tuple(warnings),
            repetition_series=tuple(repetition_series),
            rom_series=tuple(rom_series),
            bpm_series=tuple(bpm_series),
        )

    @staticmethod
    def _read_session_rows(
        path: Path,
    ) -> tuple[list[dict[str, object]], int, int]:
        parsed: list[dict[str, object]] = []
        total = 0
        invalid = 0
        with path.open(newline="") as handle:
            for raw in csv.DictReader(handle):
                total += 1
                try:
                    parsed.append({
                        "received_s": _number(raw, "received_s"),
                        "state": raw.get("state", "idle") or "idle",
                        "rep_count": int(float(raw.get("rep_count", "0"))),
                        "quality": raw.get("quality", "none") or "none",
                        "elbow_angle_deg": _number(raw, "elbow_angle_deg"),
                        "shoulder_angle_deg": _number(raw, "shoulder_angle_deg"),
                        "vision_valid": _truthy(raw.get("vision_valid", "0")),
                        "subject": (raw.get("subject", "") or "").strip(),
                    })
                except (KeyError, TypeError, ValueError):
                    invalid += 1
        return parsed, total, invalid

    @staticmethod
    def _repetitions(
        rows: list[dict[str, object]], first_time: float
    ) -> tuple[int, list[SeriesPoint]]:
        total = 0
        previous: int | None = None
        series: list[SeriesPoint] = []
        for row in rows:
            current = int(row["rep_count"])
            if previous is not None and current > previous:
                total += current - previous
                series.append(SeriesPoint(
                    round(float(row["received_s"]) - first_time, 3),
                    float(total),
                ))
            previous = current
        return total, series

    @staticmethod
    def _quality_counts(rows: list[dict[str, object]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        previous = "none"
        for row in rows:
            quality = str(row["quality"])
            if quality != "none" and quality != previous:
                counts[quality] = counts.get(quality, 0) + 1
            previous = quality
        return counts

    @staticmethod
    def _rom(
        rows: list[dict[str, object]], first_time: float
    ) -> tuple[float | None, list[SeriesPoint]]:
        maximum: float | None = None
        series: list[SeriesPoint] = []
        active_state: str | None = None
        values: list[float] = []

        for row in rows:
            state = str(row["state"])
            angle_field = SUPPORTED_ROM_STATES.get(state)
            usable = bool(row["vision_valid"]) and angle_field is not None
            if not usable:
                active_state = None
                values = []
                continue
            if state != active_state:
                active_state = state
                values = []
            values.append(float(row[angle_field]))
            if len(values) < 2:
                continue
            current_range = max(values) - min(values)
            maximum = current_range if maximum is None else max(maximum, current_range)
            series.append(SeriesPoint(
                round(float(row["received_s"]) - first_time, 3),
                round(current_range, 2),
            ))
        return (round(maximum, 2) if maximum is not None else None), series

    @staticmethod
    def _read_ecg(
        path: Path,
    ) -> tuple[float | None, float | None, list[SeriesPoint], str | None]:
        if not path.is_file():
            return None, None, [], "No ECG recording"
        total = 0
        connected = 0
        bpm_values: list[float] = []
        raw_points: list[tuple[float, float]] = []
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                total += 1
                try:
                    is_connected = _truthy(row.get("leads_connected", "0"))
                    if is_connected:
                        connected += 1
                    bpm = float(row.get("bpm", "0"))
                    received_s = float(row.get("received_s", "0"))
                    if is_connected and bpm > 0:
                        bpm_values.append(bpm)
                        raw_points.append((received_s, bpm))
                except (TypeError, ValueError):
                    continue
        completeness = round(100.0 * connected / total, 1) if total else 0.0
        if not connected:
            return None, completeness, [], "No connected ECG samples"
        origin = raw_points[0][0] if raw_points else 0.0
        series = [
            SeriesPoint(round(timestamp - origin, 3), value)
            for timestamp, value in raw_points
        ]
        average = round(sum(bpm_values) / len(bpm_values), 1) if bpm_values else None
        return average, completeness, series, None

