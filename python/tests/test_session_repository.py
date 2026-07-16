import csv
from pathlib import Path

import pytest

from literehab.dashboard_state import SESSION_FIELDS
from literehab.session_repository import SessionRepository


def session_row(
    received_s: float,
    state: str,
    rep_count: int,
    quality: str,
    *,
    elbow: float = 0.0,
    shoulder: float = 0.0,
    vision_valid: float = 1.0,
    subject: str = "Demo-01",
) -> dict[str, object]:
    row: dict[str, object] = {field: 0 for field in SESSION_FIELDS}
    row.update({
        "t_ms": int(received_s * 1000),
        "received_s": received_s,
        "state": state,
        "rep_count": rep_count,
        "quality": quality,
        "elbow_angle_deg": elbow,
        "shoulder_angle_deg": shoulder,
        "vision_valid": vision_valid,
        "subject": subject,
    })
    return row


def write_csv(path: Path, fieldnames, rows) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_report_derives_events_without_counting_repeated_rows(tmp_path):
    write_csv(
        tmp_path / "demo.csv",
        SESSION_FIELDS,
        [
            session_row(1.0, "idle", 0, "none", elbow=40),
            session_row(2.0, "elbow_flexion", 1, "ok", elbow=85),
            session_row(3.0, "elbow_flexion", 1, "ok", elbow=100),
            session_row(4.0, "elbow_flexion", 2, "too_fast", elbow=70),
        ],
    )

    report = SessionRepository(tmp_path).get_report("demo")

    assert report.duration_s == 3.0
    assert report.repetitions == 2
    assert report.exercises == ("elbow_flexion",)
    assert report.quality_counts == {"ok": 1, "too_fast": 1}
    assert report.good_form_percent == 50.0
    assert report.max_rom_deg == 30.0
    assert report.pose_completeness_percent == 100.0


def test_report_uses_only_connected_positive_bpm_samples(tmp_path):
    write_csv(
        tmp_path / "demo.csv",
        SESSION_FIELDS,
        [session_row(1.0, "idle", 0, "none")],
    )
    write_csv(
        tmp_path / "demo_ecg.csv",
        ("t_ms", "received_s", "raw_adc", "bpm", "leads_connected", "beat", "rapid_change"),
        [
            {"t_ms": 1, "received_s": 1, "raw_adc": 100, "bpm": 70, "leads_connected": 1, "beat": 0, "rapid_change": 0},
            {"t_ms": 2, "received_s": 2, "raw_adc": 101, "bpm": 0, "leads_connected": 1, "beat": 0, "rapid_change": 0},
            {"t_ms": 3, "received_s": 3, "raw_adc": 102, "bpm": 120, "leads_connected": 0, "beat": 0, "rapid_change": 0},
            {"t_ms": 4, "received_s": 4, "raw_adc": 103, "bpm": 80, "leads_connected": 1, "beat": 0, "rapid_change": 0},
        ],
    )

    report = SessionRepository(tmp_path).get_report("demo")

    assert report.average_bpm == 75.0
    assert report.ecg_completeness_percent == 75.0
    assert [point.value for point in report.bpm_series] == [70.0, 80.0]


def test_counter_reset_starts_a_new_segment(tmp_path):
    write_csv(
        tmp_path / "demo.csv",
        SESSION_FIELDS,
        [
            session_row(1.0, "elbow_flexion", 0, "none"),
            session_row(2.0, "elbow_flexion", 1, "ok"),
            session_row(3.0, "elbow_flexion", 0, "none"),
            session_row(4.0, "elbow_flexion", 1, "ok"),
        ],
    )

    report = SessionRepository(tmp_path).get_report("demo")

    assert report.repetitions == 2
    assert [point.value for point in report.repetition_series] == [1.0, 2.0]


def test_list_ignores_ecg_companion_and_marks_incomplete_data(tmp_path):
    write_csv(
        tmp_path / "partial.csv",
        SESSION_FIELDS,
        [
            session_row(1.0, "idle", 0, "none", vision_valid=0),
            session_row(2.0, "idle", 0, "none", vision_valid=0),
        ],
    )
    write_csv(tmp_path / "partial_ecg.csv", ("bpm",), [{"bpm": 0}])

    sessions = SessionRepository(tmp_path).list_sessions()

    assert [item.session_id for item in sessions] == ["partial"]
    assert sessions[0].pose_completeness_percent == 0.0
    assert sessions[0].ecg_completeness_percent == 0.0
    assert "No valid pose samples" in sessions[0].warnings


def test_unknown_or_unsafe_session_id_is_rejected(tmp_path):
    repository = SessionRepository(tmp_path)

    with pytest.raises(KeyError):
        repository.get_report("../secret")
    with pytest.raises(KeyError):
        repository.get_report("missing")
