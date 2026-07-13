import csv
import math

import pytest

from prepare_public_imu import convert_public_csv


FIELDS = [
    "DMUAccelX", "DMUAccelY", "DMUAccelZ",
    "DMRotX", "DMRotY", "DMRotZ",
    "MoveType", "RecNo", "SessionID", "UID", "Wrist", "Hertz",
]


def _write_source(path):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for index in range(8):
            writer.writerow({
                "DMUAccelX": 0.1,
                "DMUAccelY": 0.2,
                "DMUAccelZ": 0.3,
                "DMRotX": math.pi,
                "DMRotY": math.pi / 2,
                "DMRotZ": 0.0,
                "MoveType": "el-exfl",
                "RecNo": index + 1,
                "SessionID": "session-a",
                "UID": "u01",
                "Wrist": " rt",
                "Hertz": 100,
            })


def test_convert_public_csv_maps_labels_units_and_sample_rate(tmp_path):
    source = tmp_path / "public.csv"
    output = tmp_path / "converted"
    _write_source(source)

    written = convert_public_csv(
        source,
        output,
        target_hz=50,
        max_samples_per_recording=100,
    )

    assert written == {"u01_elbow_flexion_session-a_rt.csv": 4}
    with (output / "u01_elbow_flexion_session-a_rt.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["label"] == "elbow_flexion"
    assert rows[0]["subject"] == "u01"
    assert float(rows[0]["ax"]) == pytest.approx(0.1)
    assert float(rows[0]["gx"]) == pytest.approx(180.0)
    assert float(rows[0]["gy"]) == pytest.approx(90.0)


def test_convert_public_csv_ignores_left_wrist_and_unknown_actions(tmp_path):
    source = tmp_path / "public.csv"
    output = tmp_path / "converted"
    with source.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        base = {
            "DMUAccelX": 0, "DMUAccelY": 0, "DMUAccelZ": 1,
            "DMRotX": 0, "DMRotY": 0, "DMRotZ": 0,
            "RecNo": 1, "SessionID": "s", "UID": "u01", "Hertz": 100,
        }
        writer.writerow({**base, "MoveType": "el-exfl", "Wrist": "lt"})
        writer.writerow({**base, "MoveType": "unknown", "Wrist": "rt"})

    assert convert_public_csv(source, output) == {}


def test_convert_public_csv_keeps_only_one_short_session_per_subject_action(tmp_path):
    source = tmp_path / "public.csv"
    output = tmp_path / "converted"
    with source.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for session in ("first", "second"):
            writer.writerow({
                "DMUAccelX": 0, "DMUAccelY": 0, "DMUAccelZ": 1,
                "DMRotX": 0, "DMRotY": 0, "DMRotZ": 0,
                "MoveType": "wr-prsu", "RecNo": 1,
                "SessionID": session, "UID": "u01", "Wrist": "rt",
                "Hertz": 50,
            })

    written = convert_public_csv(source, output)

    assert written == {"u01_forearm_rotation_first_rt.csv": 1}
