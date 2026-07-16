import csv
import threading

import pytest

from literehab.dashboard_state import SESSION_FIELDS
from literehab.synchronization import SynchronizedSample
from literehab.telemetry import EcgTelemetrySample, TelemetrySample
from literehab.web_runtime import LiteRehabRuntime, RuntimeConfig
from literehab.web_models import LiveSnapshot


class FakeSources:
    pass


class FakeLoopSources:
    def __init__(self):
        self.started = threading.Event()
        self.stopped = threading.Event()

    def run(self, runtime, stop_event):
        runtime.update_live(
            LiveSnapshot.initial(),
            jpeg=b"test-jpeg",
        )
        self.started.set()
        stop_event.wait(1)
        self.stopped.set()


def test_session_commands_open_and_close_both_csv_files(tmp_path):
    runtime = LiteRehabRuntime(
        RuntimeConfig(sessions_dir=tmp_path),
        sources=FakeSources(),
    )

    runtime.start_session("Demo-01")

    assert runtime.recording is True
    assert runtime.snapshot().subject == "Demo-01"
    session_files = [path for path in tmp_path.glob("*.csv") if not path.name.endswith("_ecg.csv")]
    ecg_files = list(tmp_path.glob("*_ecg.csv"))
    assert len(session_files) == 1
    assert len(ecg_files) == 1

    runtime.stop_session()

    assert runtime.recording is False
    with session_files[0].open(newline="") as handle:
        assert tuple(next(csv.reader(handle))) == SESSION_FIELDS


def test_session_filename_is_safe_and_unique(tmp_path):
    runtime = LiteRehabRuntime(RuntimeConfig(sessions_dir=tmp_path), sources=FakeSources())

    runtime.start_session("Demo Person / 01")
    first_id = runtime.current_session_id
    runtime.stop_session()
    runtime.start_session("Demo Person / 01")
    second_id = runtime.current_session_id
    runtime.stop_session()

    assert first_id != second_id
    assert "/" not in first_id
    assert " " not in first_id


def test_real_runtime_rejects_invalid_session_transitions(tmp_path):
    runtime = LiteRehabRuntime(RuntimeConfig(sessions_dir=tmp_path), sources=FakeSources())

    with pytest.raises(RuntimeError, match="not recording"):
        runtime.stop_session()
    with pytest.raises(ValueError, match="Participant ID is required"):
        runtime.start_session(" ")


def test_runtime_commands_set_worker_events(tmp_path):
    runtime = LiteRehabRuntime(RuntimeConfig(sessions_dir=tmp_path), sources=FakeSources())

    runtime.recapture_baseline()
    runtime.reset_range()

    assert runtime.baseline_reset_requested is True
    assert runtime.range_reset_requested is True


def test_runtime_records_synchronized_motion_and_ecg_rows(tmp_path):
    runtime = LiteRehabRuntime(RuntimeConfig(sessions_dir=tmp_path), sources=FakeSources())
    runtime.start_session("Demo-03")
    motion = TelemetrySample(
        1000,
        (0.1, 0.2, 1.0),
        (1.0, 2.0, 3.0),
        "elbow_flexion",
        1,
        "ok",
    )
    ecg = EcgTelemetrySample(1000, 2048, 72.0, True, True, False)

    runtime.record_synchronized([
        SynchronizedSample(motion, received_s=10.0, pose=None),
    ])
    runtime.record_ecg(ecg, received_s=10.01)
    runtime.stop_session()

    session_path = next(path for path in tmp_path.glob("*.csv") if not path.name.endswith("_ecg.csv"))
    ecg_path = next(tmp_path.glob("*_ecg.csv"))
    with session_path.open(newline="") as handle:
        row = next(csv.DictReader(handle))
    with ecg_path.open(newline="") as handle:
        ecg_row = next(csv.DictReader(handle))

    assert row["subject"] == "Demo-03"
    assert row["state"] == "elbow_flexion"
    assert row["vision_valid"] == "0.0"
    assert ecg_row["raw_adc"] == "2048"
    assert ecg_row["leads_connected"] == "1"


def test_runtime_worker_lifecycle_supports_injected_sources(tmp_path):
    sources = FakeLoopSources()
    runtime = LiteRehabRuntime(RuntimeConfig(sessions_dir=tmp_path), sources=sources)

    runtime.start()

    assert sources.started.wait(1)
    assert runtime.jpeg_frame() == b"test-jpeg"

    runtime.close()

    assert sources.stopped.wait(1)
