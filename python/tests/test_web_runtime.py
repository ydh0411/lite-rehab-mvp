import pytest

from literehab.web_models import LiveSnapshot
from literehab.web_runtime import FixtureRuntime


def test_initial_snapshot_distinguishes_unavailable_values():
    snapshot = LiveSnapshot.initial()

    assert snapshot.rom_deg is None
    assert snapshot.ecg_bpm is None
    assert snapshot.serial_status == "unavailable"
    assert snapshot.camera_status == "unavailable"
    assert snapshot.recording is False


def test_fixture_runtime_updates_recording_state_and_subject():
    runtime = FixtureRuntime()

    runtime.start_session("  Demo-01  ")

    assert runtime.recording is True
    assert runtime.snapshot().subject == "Demo-01"
    assert runtime.snapshot().recording is True

    runtime.stop_session()

    assert runtime.recording is False
    assert runtime.snapshot().recording is False


def test_fixture_runtime_rejects_invalid_transitions():
    runtime = FixtureRuntime()

    with pytest.raises(ValueError, match="Participant ID is required"):
        runtime.start_session("  ")

    runtime.start_session("Demo-01")
    with pytest.raises(RuntimeError, match="already recording"):
        runtime.start_session("Demo-02")

    runtime.stop_session()
    with pytest.raises(RuntimeError, match="not recording"):
        runtime.stop_session()


def test_fixture_runtime_records_secondary_commands():
    runtime = FixtureRuntime()

    runtime.recapture_baseline()
    runtime.reset_range()

    assert runtime.baseline_resets == 1
    assert runtime.range_resets == 1

