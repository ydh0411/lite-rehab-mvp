from literehab.pose_features import PoseFeatures
from literehab.synchronization import ReceivedTelemetry, SampleSynchronizer
from literehab.telemetry import TelemetrySample


def imu(timestamp_ms: int, received_s: float) -> ReceivedTelemetry:
    return ReceivedTelemetry(
        TelemetrySample(timestamp_ms, (0.0, 0.0, 1.0), (1.0, 2.0, 3.0),
                        "idle", 0, "none"),
        received_s,
    )


def pose(timestamp_s: float) -> PoseFeatures:
    return PoseFeatures(timestamp_s, True, elbow_angle_deg=90.0,
                        shoulder_angle_deg=45.0, visibility=0.9)


def test_matches_nearest_pose_and_preserves_every_imu_sample():
    synchronizer = SampleSynchronizer(tolerance_s=0.05)
    synchronizer.add_imu(imu(0, 1.000))
    synchronizer.add_imu(imu(20, 1.020))
    synchronizer.add_imu(imu(100, 1.100))
    synchronizer.add_pose(pose(1.018))
    synchronizer.add_pose(pose(1.110))

    rows = synchronizer.drain(now_s=1.200)

    assert [row.telemetry.timestamp_ms for row in rows] == [0, 20, 100]
    assert [row.pose.timestamp_s for row in rows if row.pose] == [1.018, 1.018, 1.110]
    assert synchronizer.drain(now_s=2.0) == []


def test_expired_sample_keeps_explicit_missing_vision():
    synchronizer = SampleSynchronizer(tolerance_s=0.05)
    synchronizer.add_imu(imu(300, 2.300))

    rows = synchronizer.drain(now_s=2.400)

    assert len(rows) == 1
    assert rows[0].pose is None


def test_force_drain_flushes_recent_samples_at_shutdown():
    synchronizer = SampleSynchronizer(tolerance_s=0.05)
    synchronizer.add_imu(imu(500, 3.000))

    assert synchronizer.drain(now_s=3.010) == []
    assert len(synchronizer.drain(now_s=3.010, force=True)) == 1
