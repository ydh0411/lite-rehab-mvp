#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import queue
import threading
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import serial
from serial.tools import list_ports

from literehab.cnn import build_model
from literehab.dashboard_state import (
    CameraHealth,
    SESSION_FIELDS,
    resolve_decision,
    synchronized_row,
    trunk_compensation_active,
)
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
from literehab.telemetry import TelemetrySample, parse_telemetry_line

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

def choose_port(requested: str) -> str | None:
    if requested != "auto":
        return requested
    ports = [item.device for item in list_ports.comports()]
    for name in ports:
        if "usbmodem" in name.lower() or "usbserial" in name.lower():
            return name
    return ports[0] if ports else None


class SerialReader(threading.Thread):
    def __init__(self, port: str):
        super().__init__(daemon=True)
        self.port = port
        self.samples: queue.Queue[ReceivedTelemetry] = queue.Queue(maxsize=500)
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
                        if sample is None:
                            continue
                        if self.samples.full():
                            try:
                                self.samples.get_nowait()
                            except queue.Empty:
                                pass
                        self.samples.put_nowait(
                            ReceivedTelemetry(sample, time.monotonic()))
            except (OSError, serial.SerialException) as error:
                self.status = f"reconnecting: {error}"
                time.sleep(1)

    def close(self) -> None:
        self.stop_event.set()


class OptionalCNN:
    def __init__(self, path: Path | None):
        self.enabled = False
        self.samples = deque(maxlen=100)
        if path is None or not path.exists():
            return
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

    def update(self, sample: TelemetrySample) -> str | None:
        self.samples.append((*sample.accel_g, *sample.gyro_dps))
        if not self.enabled or len(self.samples) < self.samples.maxlen:
            return None
        values = (np.asarray(self.samples, dtype=np.float32) - self.mean) / self.std
        tensor = self.torch.tensor(values).T.unsqueeze(0)
        with self.torch.no_grad():
            index = int(self.model(tensor).argmax(dim=1).item())
        return self.labels[index]


def draw_chart(panel: np.ndarray, history: deque[TelemetrySample]) -> None:
    panel[:] = (245, 245, 245)
    cv2.putText(panel, "IMU gyroscope (deg/s)", (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 1, cv2.LINE_AA)
    if len(history) < 2:
        return
    values = np.asarray([sample.gyro_dps for sample in history], dtype=np.float32)
    scale = max(100.0, float(np.abs(values).max()))
    colors = [(40, 60, 220), (40, 170, 40), (220, 100, 40)]
    width, height = panel.shape[1], panel.shape[0]
    for axis in range(3):
        points = []
        for i, value in enumerate(values[:, axis]):
            x = int(10 + i * (width - 20) / max(1, len(values) - 1))
            y = int(height / 2 - value * (height * 0.38) / scale)
            points.append((x, y))
        cv2.polylines(panel, [np.asarray(points)], False, colors[axis], 2)
    cv2.line(panel, (10, height // 2), (width - 10, height // 2), (120, 120, 120), 1)
    cv2.putText(panel, "X red   Y green   Z blue", (15, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1, cv2.LINE_AA)


def draw_pose(frame: np.ndarray, landmarks) -> None:
    h, w = frame.shape[:2]
    for connection in POSE_CONNECTIONS:
        a_idx, b_idx = connection
        a, b = landmarks[a_idx], landmarks[b_idx]
        if a.visibility > 0.5 and b.visibility > 0.5:
            cv2.line(frame, (int(a.x * w), int(a.y * h)),
                     (int(b.x * w), int(b.y * h)), (0, 255, 0), 1)
    for lm in landmarks:
        if lm.visibility > 0.5:
            cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 2, (0, 0, 255), -1)


def main() -> None:
    parser = argparse.ArgumentParser(description="LiteRehab live fusion dashboard")
    parser.add_argument("--port", default="auto")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--output", type=Path, default=Path("sessions/session.csv"))
    parser.add_argument("--model", type=Path)
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
    args = parser.parse_args()

    if not 0.0 <= args.model_confidence <= 1.0:
        raise SystemExit("--model-confidence must be between 0 and 1")
    if args.headless_smoke_test:
        CameraHealth()
        SampleSynchronizer()
        print("LiteRehab dashboard smoke test: PASS")
        return

    port = choose_port(args.port)
    if port is None:
        raise SystemExit("No ESP32-S3 serial port found")
    reader = SerialReader(port)
    cnn = OptionalCNN(args.model)
    multimodal = (MultimodalPredictor(load_multimodal_checkpoint(args.fusion_model))
                  if args.fusion_model is not None else None)
    synchronizer = SampleSynchronizer()
    history: deque[TelemetrySample] = deque(maxlen=250)
    latest: TelemetrySample | None = None
    cnn_prediction = None
    multimodal_prediction = None

    args.output.parent.mkdir(parents=True, exist_ok=True)
    log_file = args.output.open("w", newline="")
    log = csv.DictWriter(log_file, fieldnames=SESSION_FIELDS)
    log.writeheader()

    capture = cv2.VideoCapture(args.camera)
    camera_configured = capture.isOpened() and mp is not None
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

            camera_time = time.monotonic()
            ok, frame = capture.read() if capture.isOpened() else (False, None)
            camera_healthy = (camera_configured and camera_health.record(ok))
            if not ok:
                frame = np.zeros((600, 800, 3), dtype=np.uint8)
                cv2.putText(frame, "Camera unavailable - IMU-only mode", (70, 300),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 180, 255), 2)
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
            overlay = [
                f"Mode: {fusion.mode} ({decision.source})",
                f"Side: {args.side}",
                f"Exercise: {decision.exercise}", f"Repetitions: {reps}",
                f"Feedback: {fusion.feedback}", f"Serial: {reader.status}",
                f"ROM: {elbow_range:.1f} deg" if elbow_range is not None else "ROM: --",
                (f"Fusion confidence: {decision.confidence:.2f}"
                 if multimodal_prediction is not None
                 else f"IMU CNN: {cnn_prediction or 'not loaded'}"),
            ]
            for i, text in enumerate(overlay):
                cv2.putText(frame, text, (15, 30 + i * 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.62, (30, 240, 255), 2, cv2.LINE_AA)

            chart = np.zeros((600, 480, 3), dtype=np.uint8)
            draw_chart(chart, history)
            canvas = np.hstack((frame, chart))
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
        capture.release()
        if pose is not None:
            pose.close()
        log_file.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
