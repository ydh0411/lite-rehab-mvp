from __future__ import annotations

import csv
import queue
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Protocol

from .dashboard_state import SESSION_FIELDS, synchronized_row
from .multimodal import MultimodalPrediction
from .synchronization import SynchronizedSample
from .telemetry import EcgTelemetrySample
from .web_models import LiveSnapshot


ECG_FIELDS = (
    "t_ms", "received_s", "raw_adc", "bpm", "leads_connected", "beat",
    "rapid_change",
)


class RuntimeProtocol(Protocol):
    recording: bool

    def snapshot(self) -> LiveSnapshot: ...
    def start_session(self, subject: str) -> None: ...
    def stop_session(self) -> None: ...
    def recapture_baseline(self) -> None: ...
    def reset_range(self) -> None: ...
    def jpeg_frame(self) -> bytes | None: ...
    def start(self) -> None: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class RuntimeConfig:
    port: str = "auto"
    camera_source: int | str = 0
    side: str = "right"
    sessions_dir: Path = Path("python/sessions")
    model: Path | None = None
    fusion_model: Path | None = None
    model_confidence: float = 0.70


@dataclass
class _SessionWriters:
    session_id: str
    subject: str
    log_file: object
    log: csv.DictWriter
    ecg_file: object
    ecg_log: csv.DictWriter

    def close(self) -> None:
        self.log_file.close()
        self.ecg_file.close()


class LiteRehabRuntime:
    def __init__(self, config: RuntimeConfig, sources: object | None = None) -> None:
        if config.side not in {"left", "right"}:
            raise ValueError("side must be left or right")
        if not 0.0 <= config.model_confidence <= 1.0:
            raise ValueError("model_confidence must be between 0 and 1")
        self.config = config
        self.sources = sources
        self.recording = False
        self.current_session_id = ""
        self.baseline_reset_requested = False
        self.range_reset_requested = False
        self._snapshot = replace(LiveSnapshot.initial(), side=config.side)
        self._lock = threading.RLock()
        self._writers: _SessionWriters | None = None
        self._session_counter = 0
        self._jpeg: bytes | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.worker_error: str | None = None

    def snapshot(self) -> LiveSnapshot:
        with self._lock:
            return self._snapshot

    def start_session(self, subject: str) -> None:
        normalized = subject.strip()
        if not normalized:
            raise ValueError("Participant ID is required")
        with self._lock:
            if self.recording:
                raise RuntimeError("Session is already recording")
            self.config.sessions_dir.mkdir(parents=True, exist_ok=True)
            self._session_counter += 1
            safe_subject = re.sub(r"[^A-Za-z0-9_-]+", "-", normalized).strip("-")
            safe_subject = safe_subject or "participant"
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            session_id = f"{stamp}-{self._session_counter:02d}-{safe_subject}"
            session_path = self.config.sessions_dir / f"{session_id}.csv"
            ecg_path = self.config.sessions_dir / f"{session_id}_ecg.csv"
            log_file = session_path.open("w", newline="")
            ecg_file = ecg_path.open("w", newline="")
            log = csv.DictWriter(log_file, fieldnames=SESSION_FIELDS)
            ecg_log = csv.DictWriter(ecg_file, fieldnames=ECG_FIELDS)
            log.writeheader()
            ecg_log.writeheader()
            log_file.flush()
            ecg_file.flush()
            self._writers = _SessionWriters(
                session_id, normalized, log_file, log, ecg_file, ecg_log
            )
            self.recording = True
            self.current_session_id = session_id
            self._snapshot = replace(
                self._snapshot,
                recording=True,
                subject=normalized,
                repetitions=0,
            )

    def stop_session(self) -> None:
        with self._lock:
            if not self.recording or self._writers is None:
                raise RuntimeError("Session is not recording")
            self._writers.close()
            self._writers = None
            self.recording = False
            self._snapshot = replace(self._snapshot, recording=False)

    def recapture_baseline(self) -> None:
        self.baseline_reset_requested = True

    def reset_range(self) -> None:
        self.range_reset_requested = True

    def jpeg_frame(self) -> bytes | None:
        with self._lock:
            return self._jpeg

    def update_live(self, snapshot: LiveSnapshot, jpeg: bytes | None = None) -> None:
        with self._lock:
            self._snapshot = replace(
                snapshot,
                recording=self.recording,
                subject=(self._writers.subject if self._writers is not None else self._snapshot.subject),
            )
            if jpeg is not None:
                self._jpeg = jpeg

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Runtime is already running")
        self._stop_event.clear()
        self.worker_error = None
        self._thread = threading.Thread(
            target=self._worker_entry,
            name="literehab-web-runtime",
            daemon=True,
        )
        self._thread.start()

    def _worker_entry(self) -> None:
        try:
            runner = getattr(self.sources, "run", None)
            if callable(runner):
                runner(self, self._stop_event)
            else:
                self._run_hardware()
        except Exception as error:  # runtime health is surfaced in the UI
            self.worker_error = f"{type(error).__name__}: {error}"
            with self._lock:
                self._snapshot = replace(
                    self._snapshot,
                    serial_status=f"runtime failure: {error}",
                    camera_status="unavailable",
                )

    def close(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        with self._lock:
            if self._writers is not None:
                self._writers.close()
                self._writers = None
            self.recording = False
            self._snapshot = replace(self._snapshot, recording=False)

    def _run_hardware(self) -> None:
        import cv2
        import numpy as np

        from run_dashboard import (
            MP_LEGACY,
            OptionalCNN,
            SerialReader,
            choose_port,
            draw_pose,
            mp,
            mp_tasks,
            mp_vision,
        )

        from .camera_source import CameraSource
        from .dashboard_state import (
            CameraHealth,
            resolve_decision,
            trunk_compensation_active,
        )
        from .fusion import fuse_feedback
        from .multimodal import (
            POSE_FEATURE_NAMES,
            MultimodalPredictor,
            load_multimodal_checkpoint,
        )
        from .pose_features import (
            SIDE_INDICES,
            PoseFeatures,
            RepetitionRangeTracker,
            extract_pose_features,
        )
        from .synchronization import SampleSynchronizer

        cnn = OptionalCNN(self.config.model)
        multimodal = (
            MultimodalPredictor(load_multimodal_checkpoint(self.config.fusion_model))
            if self.config.fusion_model is not None
            else None
        )
        synchronizer = SampleSynchronizer()
        ecg_history: deque[EcgTelemetrySample] = deque(maxlen=500)
        latest = None
        latest_ecg: EcgTelemetrySample | None = None
        cnn_prediction: str | None = None
        multimodal_prediction: MultimodalPrediction | None = None

        port = choose_port(self.config.port)
        reader = SerialReader(port) if port is not None else None
        if reader is not None:
            reader.start()

        camera = CameraSource(self.config.camera_source, cv2)
        camera_health = CameraHealth()
        camera_configured = mp is not None
        pose = None
        if camera_configured and MP_LEGACY:
            pose = mp.solutions.pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        elif camera_configured:
            model_path = Path(__file__).resolve().parents[1] / "models" / "pose_landmarker_lite.task"
            if model_path.exists():
                base_options = mp_tasks.BaseOptions(model_asset_path=str(model_path))
                options = mp_vision.PoseLandmarkerOptions(
                    base_options=base_options,
                    running_mode=mp_vision.RunningMode.VIDEO,
                    num_poses=1,
                    min_pose_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
                pose = mp_vision.PoseLandmarker.create_from_options(options)
            else:
                camera_configured = False

        baseline = None
        previous_pose: PoseFeatures | None = None
        range_tracker = RepetitionRangeTracker()
        previous_recording = False
        previous_rep_count: int | None = None
        session_repetitions = 0
        last_camera_frame_s: float | None = None
        last_port_probe_s = time.monotonic()

        try:
            while not self._stop_event.is_set():
                now = time.monotonic()
                if reader is None and now - last_port_probe_s >= 2.0:
                    port = choose_port(self.config.port)
                    last_port_probe_s = now
                    if port is not None:
                        reader = SerialReader(port)
                        reader.start()

                if self.recording and not previous_recording:
                    synchronizer = SampleSynchronizer()
                    previous_rep_count = None
                    session_repetitions = 0
                previous_recording = self.recording

                if reader is not None:
                    while True:
                        try:
                            received = reader.samples.get_nowait()
                        except queue.Empty:
                            break
                        latest = received.sample
                        synchronizer.add_imu(received)
                        cnn_prediction = cnn.update(latest) or cnn_prediction
                        if self.recording:
                            if previous_rep_count is not None and latest.rep_count > previous_rep_count:
                                session_repetitions += latest.rep_count - previous_rep_count
                            previous_rep_count = latest.rep_count

                    while True:
                        try:
                            received_ecg = reader.ecg_samples.get_nowait()
                        except queue.Empty:
                            break
                        latest_ecg = received_ecg.sample
                        ecg_history.append(latest_ecg)
                        self.record_ecg(latest_ecg, received_ecg.received_s)

                if self.baseline_reset_requested:
                    baseline = None
                    self.baseline_reset_requested = False
                if self.range_reset_requested:
                    range_tracker.reset()
                    self.range_reset_requested = False

                camera_time = time.monotonic()
                ok, frame = camera.read()
                camera_healthy = (
                    camera_configured and camera.healthy and camera_health.record(ok)
                )
                if not ok or frame is None:
                    frame = np.zeros((540, 960, 3), dtype=np.uint8)
                else:
                    frame = cv2.resize(frame, (960, 540))
                    last_camera_frame_s = camera_time

                current_pose: PoseFeatures | None = None
                landmarks = None
                if ok and camera_healthy and pose is not None:
                    if MP_LEGACY:
                        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        if results.pose_landmarks:
                            mp.solutions.drawing_utils.draw_landmarks(
                                frame,
                                results.pose_landmarks,
                                mp.solutions.pose.POSE_CONNECTIONS,
                            )
                            landmarks = results.pose_landmarks.landmark
                    else:
                        mp_image = mp.Image(
                            image_format=mp.ImageFormat.SRGB,
                            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                        )
                        results = pose.detect_for_video(
                            mp_image,
                            int(camera_time * 1000),
                        )
                        if results.pose_landmarks:
                            landmarks = results.pose_landmarks[0]
                            draw_pose(frame, landmarks)

                    if landmarks is not None:
                        current_pose = extract_pose_features(
                            landmarks,
                            self.config.side,
                            camera_time,
                            baseline,
                            previous_pose,
                        )
                        synchronizer.add_pose(current_pose)
                        if current_pose.valid:
                            indices = SIDE_INDICES[self.config.side]
                            if baseline is None:
                                baseline = {
                                    "shoulder": (
                                        landmarks[indices["shoulder"]].x,
                                        landmarks[indices["shoulder"]].y,
                                    ),
                                    "hip": (
                                        landmarks[indices["hip"]].x,
                                        landmarks[indices["hip"]].y,
                                    ),
                                }
                            previous_pose = current_pose

                ready = synchronizer.drain(time.monotonic())
                for synchronized in ready:
                    pose_values = (
                        synchronized.pose.to_vector()
                        if synchronized.pose is not None
                        else (0.0,) * len(POSE_FEATURE_NAMES)
                    )
                    if multimodal is not None:
                        sample = synchronized.telemetry
                        multimodal_prediction = multimodal.update(
                            (*sample.accel_g, *sample.gyro_dps),
                            pose_values,
                        )
                    self.record_synchronized([synchronized], multimodal_prediction)

                rule_state = latest.state if latest is not None else "idle"
                rule_quality = latest.quality if latest is not None else "none"
                decision = resolve_decision(
                    rule_state,
                    rule_quality,
                    multimodal_prediction,
                    self.config.model_confidence,
                )
                device_repetitions = latest.rep_count if latest is not None else 0
                shown_repetitions = session_repetitions if self.recording else device_repetitions
                elbow_angle = (
                    current_pose.elbow_angle_deg
                    if current_pose is not None and current_pose.valid
                    else None
                )
                elbow_range = range_tracker.update(
                    rule_state,
                    shown_repetitions,
                    elbow_angle,
                )
                trunk_flag = trunk_compensation_active(rule_state, current_pose)
                vision_valid = bool(current_pose is not None and current_pose.valid)
                fusion = fuse_feedback(
                    decision.exercise,
                    decision.quality,
                    elbow_range,
                    trunk_flag,
                    vision_valid,
                )
                confidence_text = (
                    f"Fusion {decision.confidence:.2f}"
                    if multimodal_prediction is not None
                    else cnn.status_text(cnn_prediction)
                )
                camera_age = (
                    None
                    if last_camera_frame_s is None
                    else max(0.0, time.monotonic() - last_camera_frame_s)
                )
                snapshot = LiveSnapshot(
                    timestamp_s=time.monotonic(),
                    recording=self.recording,
                    subject=self.snapshot().subject,
                    exercise=decision.exercise,
                    repetitions=shown_repetitions,
                    feedback=fusion.feedback,
                    mode=fusion.mode,
                    source=decision.source,
                    side=self.config.side,
                    serial_status=(
                        reader.status
                        if reader is not None
                        else "unavailable: no ESP32-S3 serial port"
                    ),
                    camera_status=camera.status,
                    rom_deg=elbow_range,
                    confidence_text=confidence_text,
                    model_confidence=(
                        decision.confidence
                        if multimodal_prediction is not None
                        else None
                    ),
                    ecg_bpm=(
                        latest_ecg.bpm
                        if latest_ecg is not None and latest_ecg.leads_connected
                        else None
                    ),
                    ecg_connected=bool(
                        latest_ecg is not None and latest_ecg.leads_connected
                    ),
                    ecg_samples=tuple(float(item.raw_adc) for item in ecg_history),
                    camera_frame_age_s=camera_age,
                )
                encoded_ok, encoded = cv2.imencode(
                    ".jpg",
                    frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 82],
                )
                self.update_live(
                    snapshot,
                    encoded.tobytes() if encoded_ok else None,
                )
                self._stop_event.wait(0.01)
        finally:
            remaining = synchronizer.drain(time.monotonic(), force=True)
            self.record_synchronized(remaining, multimodal_prediction)
            if reader is not None:
                reader.close()
            camera.close()
            if pose is not None:
                pose.close()

    def record_synchronized(
        self,
        rows: list[SynchronizedSample],
        prediction: MultimodalPrediction | None = None,
    ) -> None:
        with self._lock:
            if self._writers is None:
                return
            for synchronized in rows:
                self._writers.log.writerow(synchronized_row(
                    synchronized,
                    prediction,
                    self._writers.subject,
                ))
            if rows:
                self._writers.log_file.flush()

    def record_ecg(self, sample: EcgTelemetrySample, received_s: float) -> None:
        with self._lock:
            if self._writers is None:
                return
            self._writers.ecg_log.writerow({
                "t_ms": sample.timestamp_ms,
                "received_s": received_s,
                "raw_adc": sample.raw_adc,
                "bpm": sample.bpm,
                "leads_connected": int(sample.leads_connected),
                "beat": int(sample.beat),
                "rapid_change": int(sample.rapid_change),
            })
            self._writers.ecg_file.flush()


class FixtureRuntime:
    def __init__(self) -> None:
        self.recording = False
        self.subject = ""
        self.baseline_resets = 0
        self.range_resets = 0
        self._snapshot = LiveSnapshot.initial()

    def snapshot(self) -> LiveSnapshot:
        return self._snapshot

    def start_session(self, subject: str) -> None:
        normalized = subject.strip()
        if not normalized:
            raise ValueError("Participant ID is required")
        if self.recording:
            raise RuntimeError("Session is already recording")
        self.recording = True
        self.subject = normalized
        self._snapshot = replace(
            self._snapshot,
            recording=True,
            subject=normalized,
        )

    def stop_session(self) -> None:
        if not self.recording:
            raise RuntimeError("Session is not recording")
        self.recording = False
        self._snapshot = replace(self._snapshot, recording=False)

    def recapture_baseline(self) -> None:
        self.baseline_resets += 1

    def reset_range(self) -> None:
        self.range_resets += 1

    def jpeg_frame(self) -> bytes | None:
        return None

    def set_snapshot(self, snapshot: LiveSnapshot) -> None:
        self._snapshot = snapshot
        self.recording = snapshot.recording
        self.subject = snapshot.subject
