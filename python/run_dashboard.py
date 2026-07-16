#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import serial
from serial.tools import list_ports

from literehab.camera_source import CameraSource, parse_camera_source
from literehab.cnn import build_model
from literehab.dashboard_state import (
    CameraHealth,
    SESSION_FIELDS,
    resolve_decision,
    synchronized_row,
    trunk_compensation_active,
)
from literehab.dashboard_view import DashboardViewState, render_dashboard
from literehab.fusion import fuse_feedback
from literehab.multimodal import (
    POSE_FEATURE_NAMES,
    MultimodalPredictor,
    load_multimodal_checkpoint,
)
from literehab.pose_features import (
    SIDE_INDICES,
    PoseFeatures,
    RepetitionRangeTracker,
    extract_pose_features,
)
from literehab.synchronization import ReceivedTelemetry, SampleSynchronizer
from literehab.telemetry import (
    EcgTelemetrySample,
    TelemetrySample,
    parse_ecg_line,
    parse_telemetry_line,
)

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_tasks
    from mediapipe.tasks.python import vision as mp_vision
    _ = mp.solutions
    MP_LEGACY = True
except (ImportError, AttributeError):
    MP_LEGACY = False
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_tasks
        from mediapipe.tasks.python import vision as mp_vision
    except ImportError:
        mp = None
        mp_tasks = None
        mp_vision = None

POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    (17, 19), (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32),
]

POSE_LINE_COLOR = (212, 184, 62)
POSE_JOINT_COLOR = (244, 219, 118)
POSE_JOINT_OUTLINE = (31, 24, 14)
ECG_FIELDS = (
    "t_ms", "received_s", "raw_adc", "bpm", "leads_connected", "beat",
    "rapid_change",
)


@dataclass(frozen=True)
class ReceivedEcg:
    sample: EcgTelemetrySample
    received_s: float


def put_latest(target: queue.Queue, value) -> None:
    if target.full():
        try:
            target.get_nowait()
        except queue.Empty:
            pass
    target.put_nowait(value)


def ecg_output_path(session_path: Path) -> Path:
    suffix = session_path.suffix or ".csv"
    return session_path.with_name(f"{session_path.stem}_ecg{suffix}")


def choose_port(requested: str) -> str | None:
    if requested != "auto":
        return requested
    ports = [item.device for item in list_ports.comports()]
    for name in ports:
        if "usbmodem" in name.lower():
            return name
    for name in ports:
        if "usbserial" in name.lower():
            return name
    return ports[0] if ports else None


class SerialReader(threading.Thread):
    def __init__(self, port: str):
        super().__init__(daemon=True)
        self.port = port
        self.samples: queue.Queue[ReceivedTelemetry] = queue.Queue(maxsize=500)
        self.ecg_samples: queue.Queue[ReceivedEcg] = queue.Queue(maxsize=1000)
        self.stop_event = threading.Event()
        self.status = "connecting"

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                with serial.Serial(self.port, 115200, timeout=1) as device:
                    self.status = "connected"
                    while not self.stop_event.is_set():
                        line = device.readline().decode("utf-8", "ignore")
                        sample = parse_telemetry_line(line)
                        received_s = time.monotonic()
                        if sample is not None:
                            put_latest(
                                self.samples,
                                ReceivedTelemetry(sample, received_s),
                            )
                            continue
                        ecg_sample = parse_ecg_line(line)
                        if ecg_sample is not None:
                            put_latest(
                                self.ecg_samples,
                                ReceivedEcg(ecg_sample, received_s),
                            )
            except (OSError, serial.SerialException) as error:
                self.status = f"reconnecting: {error}"
                time.sleep(1)

    def close(self) -> None:
        self.stop_event.set()


class OptionalCNN:
    def __init__(self, path: Path | None):
        self.enabled = False
        self.samples = deque(maxlen=100)
        self.path = path
        if path is None:
            return
        if not path.exists():
            raise FileNotFoundError(f"IMU CNN checkpoint not found: {path}")
        import torch
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        self.labels = checkpoint["labels"]
        self.mean = np.asarray(checkpoint["mean"], dtype=np.float32)
        self.std = np.asarray(checkpoint["std"], dtype=np.float32)
        arch = checkpoint.get("arch", "cnn_1d")
        self.model = build_model(len(self.labels), arch=arch)
        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.eval()
        self.torch = torch
        self.enabled = True

    def status_text(self, prediction: str | None) -> str:
        if not self.enabled:
            return "disabled"
        if prediction is None:
            return f"warming up ({len(self.samples)}/{self.samples.maxlen})"
        return prediction

    def update(self, sample: TelemetrySample) -> str | None:
        self.samples.append((*sample.accel_g, *sample.gyro_dps))
        if not self.enabled or len(self.samples) < self.samples.maxlen:
            return None
        if sample.state == "idle":
            return "idle"
        values = (np.asarray(self.samples, dtype=np.float32) - self.mean) / self.std
        tensor = self.torch.tensor(values).T.unsqueeze(0)
        with self.torch.no_grad():
            index = int(self.model(tensor).argmax(dim=1).item())
        return self.labels[index]


def draw_pose(frame: np.ndarray, landmarks) -> None:
    h, w = frame.shape[:2]
    for a_idx, b_idx in POSE_CONNECTIONS:
        a, b = landmarks[a_idx], landmarks[b_idx]
        if a.visibility > 0.5 and b.visibility > 0.5:
            cv2.line(
                frame,
                (int(a.x * w), int(a.y * h)),
                (int(b.x * w), int(b.y * h)),
                POSE_LINE_COLOR,
                2,
                cv2.LINE_AA,
            )
    for landmark in landmarks:
        if landmark.visibility > 0.5:
            center = (int(landmark.x * w), int(landmark.y * h))
            cv2.circle(frame, center, 4, POSE_JOINT_OUTLINE, -1, cv2.LINE_AA)
            cv2.circle(frame, center, 2, POSE_JOINT_COLOR, -1, cv2.LINE_AA)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LiteRehab live fusion dashboard")
    parser.add_argument("--port", default="auto")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument(
        "--camera-source",
        help="auto, a local UVC camera index, or an rtsp:// URL",
    )
    parser.add_argument("--output", type=Path, default=Path("sessions/session.csv"))
    parser.add_argument(
        "--model",
        type=Path,
        default=Path(__file__).resolve().parent / "models" / "imu_cnnbigru.pt",
    )
    parser.add_argument("--fusion-model", type=Path)
    parser.add_argument("--model-confidence", type=float, default=0.70)
    parser.add_argument("--side", choices=["left", "right"], default="left")
    parser.add_argument("--subject", default="")
    parser.add_argument(
        "--label-exercise", default="",
        choices=["", "idle", "forearm_rotation", "elbow_flexion",
                 "shoulder_abduction"])
    parser.add_argument(
        "--label-quality", default="",
        choices=["", "none", "ok", "too_fast", "insufficient_range",
                 "trunk_compensation"])
    parser.add_argument("--headless-smoke-test", action="store_true")
    return parser


def resolve_camera_argument(args: argparse.Namespace) -> int | str:
    selected = args.camera_source if args.camera_source is not None else args.camera
    try:
        return parse_camera_source(selected)
    except ValueError as error:
        raise SystemExit(str(error)) from error


def main() -> None:
    args = build_parser().parse_args()

    if not 0.0 <= args.model_confidence <= 1.0:
        raise SystemExit("--model-confidence must be between 0 and 1")
    cnn = OptionalCNN(args.model)
    if args.headless_smoke_test:
        CameraHealth()
        SampleSynchronizer()
        print(f"IMU CNN loaded: {args.model}")
        print("LiteRehab dashboard smoke test: PASS")
        return

    camera_argument = resolve_camera_argument(args)

    port = choose_port(args.port)
    if port is None:
        raise SystemExit("No ESP32-S3 serial port found")
    reader = SerialReader(port)
    multimodal = (MultimodalPredictor(load_multimodal_checkpoint(args.fusion_model))
                  if args.fusion_model is not None else None)
    synchronizer = SampleSynchronizer()
    history: deque[TelemetrySample] = deque(maxlen=250)
    ecg_history: deque[EcgTelemetrySample] = deque(maxlen=500)
    latest: TelemetrySample | None = None
    latest_ecg: EcgTelemetrySample | None = None
    cnn_prediction = None
    multimodal_prediction = None

    args.output.parent.mkdir(parents=True, exist_ok=True)
    log_file = args.output.open("w", newline="")
    log = csv.DictWriter(log_file, fieldnames=SESSION_FIELDS)
    log.writeheader()
    ecg_path = ecg_output_path(args.output)
    ecg_log_file = ecg_path.open("w", newline="")
    ecg_log = csv.DictWriter(ecg_log_file, fieldnames=ECG_FIELDS)
    ecg_log.writeheader()

    camera = CameraSource(camera_argument, cv2)
    camera_configured = mp is not None
    camera_health = CameraHealth()
    if camera_configured and MP_LEGACY:
        pose = mp.solutions.pose.Pose(min_detection_confidence=0.5,
                                       min_tracking_confidence=0.5)
    elif camera_configured:
        model_path = Path(__file__).parent / "models" / "pose_landmarker_lite.task"
        if model_path.exists():
            base_opts = mp_tasks.BaseOptions(model_asset_path=str(model_path))
            opts = mp_vision.PoseLandmarkerOptions(
                base_options=base_opts,
                running_mode=mp_vision.RunningMode.VIDEO,
                num_poses=1,
                min_pose_detection_confidence=0.5,
                min_tracking_confidence=0.5)
            pose = mp_vision.PoseLandmarker.create_from_options(opts)
        else:
            print(f"Model not found: {model_path}, falling back to IMU-only")
            camera_configured = False
            pose = None
    else:
        pose = None
    baseline = None
    previous_pose: PoseFeatures | None = None
    range_tracker = RepetitionRangeTracker()

    def record_ready(rows) -> None:
        nonlocal multimodal_prediction
        for synchronized in rows:
            pose_values = (synchronized.pose.to_vector()
                           if synchronized.pose is not None
                           else (0.0,) * len(POSE_FEATURE_NAMES))
            if multimodal is not None:
                sample = synchronized.telemetry
                multimodal_prediction = multimodal.update(
                    (*sample.accel_g, *sample.gyro_dps), pose_values)
            log.writerow(synchronized_row(
                synchronized, multimodal_prediction, args.subject,
                args.label_exercise, args.label_quality))
        if rows:
            log_file.flush()

    reader.start()
    try:
        while True:
            while True:
                try:
                    received = reader.samples.get_nowait()
                except queue.Empty:
                    break
                latest = received.sample
                synchronizer.add_imu(received)
                history.append(latest)
                cnn_prediction = cnn.update(latest) or cnn_prediction

            drained_ecg = False
            while True:
                try:
                    received_ecg = reader.ecg_samples.get_nowait()
                except queue.Empty:
                    break
                latest_ecg = received_ecg.sample
                ecg_history.append(latest_ecg)
                ecg_log.writerow({
                    "t_ms": latest_ecg.timestamp_ms,
                    "received_s": received_ecg.received_s,
                    "raw_adc": latest_ecg.raw_adc,
                    "bpm": latest_ecg.bpm,
                    "leads_connected": int(latest_ecg.leads_connected),
                    "beat": int(latest_ecg.beat),
                    "rapid_change": int(latest_ecg.rapid_change),
                })
                drained_ecg = True
            if drained_ecg:
                ecg_log_file.flush()

            camera_time = time.monotonic()
            ok, frame = camera.read()
            camera_healthy = (
                camera_configured and camera.healthy and camera_health.record(ok)
            )
            if not ok:
                frame = np.zeros((600, 800, 3), dtype=np.uint8)
            else:
                frame = cv2.resize(frame, (800, 600))

            current_pose: PoseFeatures | None = None
            landmarks = None
            if ok and camera_healthy and pose is not None:
                if MP_LEGACY:
                    results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    if results.pose_landmarks:
                        mp.solutions.drawing_utils.draw_landmarks(
                            frame, results.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
                        landmarks = results.pose_landmarks.landmark
                else:
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,
                                        data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    results = pose.detect_for_video(
                        mp_image, int(camera_time * 1000))
                    if results.pose_landmarks:
                        landmarks = results.pose_landmarks[0]
                        draw_pose(frame, landmarks)
                if landmarks is not None:
                    current_pose = extract_pose_features(
                        landmarks, args.side, camera_time, baseline, previous_pose)
                    synchronizer.add_pose(current_pose)
                    if current_pose.valid:
                        indices = SIDE_INDICES[args.side]
                        if baseline is None:
                            baseline = {
                                "shoulder": (
                                    landmarks[indices["shoulder"]].x,
                                    landmarks[indices["shoulder"]].y),
                                "hip": (landmarks[indices["hip"]].x,
                                        landmarks[indices["hip"]].y),
                            }
                        previous_pose = current_pose

            record_ready(synchronizer.drain(time.monotonic()))
            rule_state = latest.state if latest else "idle"
            rule_quality = latest.quality if latest else "none"
            decision = resolve_decision(
                rule_state, rule_quality, multimodal_prediction,
                args.model_confidence)
            reps = latest.rep_count if latest else 0
            elbow_angle = (current_pose.elbow_angle_deg
                           if current_pose is not None and current_pose.valid
                           else None)
            elbow_range = range_tracker.update(rule_state, reps, elbow_angle)
            trunk_flag = trunk_compensation_active(rule_state, current_pose)
            vision_valid = bool(current_pose is not None and current_pose.valid)
            fusion = fuse_feedback(decision.exercise, decision.quality,
                                   elbow_range, trunk_flag, vision_valid)
            confidence_text = (
                f"Fusion {decision.confidence:.2f}"
                if multimodal_prediction is not None
                else cnn.status_text(cnn_prediction)
            )
            view_state = DashboardViewState(
                exercise=decision.exercise,
                repetitions=reps,
                feedback=fusion.feedback,
                mode=fusion.mode,
                source=decision.source,
                side=args.side,
                serial_status=reader.status,
                camera_status=camera.status,
                rom_deg=elbow_range,
                confidence_text=confidence_text,
                ecg_bpm=(latest_ecg.bpm if latest_ecg is not None else None),
                ecg_connected=bool(
                    latest_ecg is not None and latest_ecg.leads_connected
                ),
            )
            canvas = render_dashboard(frame, history, view_state, ecg_history)
            cv2.imshow("LiteRehab-Fusion MVP", canvas)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            if key == ord("b"):
                baseline = None
            if key == ord("r"):
                range_tracker.reset()
    finally:
        record_ready(synchronizer.drain(time.monotonic(), force=True))
        reader.close()
        camera.close()
        if pose is not None:
            pose.close()
        log_file.close()
        ecg_log_file.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
