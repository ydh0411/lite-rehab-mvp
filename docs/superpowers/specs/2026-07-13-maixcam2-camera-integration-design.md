# MaixCAM 2 Camera Integration Design

**Date:** 2026-07-13  
**Status:** Approved for implementation planning

## Objective

Use a MaixCAM 2 as the vision sensor for the LiteRehab MVP without changing the existing wearable, BLE receiver, pose-feature, rehabilitation-feedback, or CSV semantics. The live demonstration must use USB UVC by default and retain RTSP as a practical backup.

## Scope

The change includes:

- a MaixPy application for MaixCAM 2 with selectable UVC and RTSP output;
- a tested desktop camera-source abstraction for local UVC devices and network stream URLs;
- bounded reconnect and frame-health behavior;
- camera discovery and launch helpers;
- updated setup, connection, troubleshooting, and demonstration instructions.

Running pose inference on the MaixCAM 2 NPU, changing the rehabilitation model, and changing BLE firmware are outside this integration.

## Architecture

### MaixCAM 2 application

One MaixPy entry point accepts `uvc` or `rtsp` mode.

- **UVC mode:** read the built-in camera at 640 x 480 and send MJPEG frames through `maix.uvc.UvcStreamer`. This is the default demonstration path because it does not depend on venue Wi-Fi.
- **RTSP mode:** expose the built-in camera as an NV21 stream at `rtsp://<device-ip>:8554/live` using `maix.rtsp.Rtsp`. This is the backup path when the host cannot use the UVC device.

The application shows its active mode and connection information on the MaixCAM 2 display where the selected MaixPy API permits it. It exits through the normal Maix application exit signal.

### Desktop camera input

A new `literehab.camera_source` module owns source parsing, OpenCV capture construction, frame reads, and recovery. The dashboard consumes its small interface rather than constructing `cv2.VideoCapture` directly.

Accepted source values are:

- an integer-like value such as `0` or `1` for a local UVC device;
- an RTSP URL such as `rtsp://10.131.167.1:8554/live`;
- `auto`, which probes a bounded set of local camera indices and selects the first source that returns a valid frame.

The existing `--camera` argument remains accepted for backward compatibility. A clearer `--camera-source` argument is added and takes precedence when supplied.

### Data flow

```text
MaixCAM 2 sensor -> UVC or RTSP -> camera source -> MediaPipe pose
                                                        |
right-arm wearable -> BLE -> ESP32-S3 receiver -> serial +-> fusion -> dashboard/CSV
```

Timestamps remain desktop monotonic timestamps taken when a frame is received. This preserves the current nearest-neighbor RGB/IMU association behavior.

## Failure and Recovery Behavior

- A single failed read does not permanently disable vision.
- Consecutive failed reads mark the camera unhealthy and place feedback in `IMU-only` mode.
- Reopening is rate-limited so an unavailable source does not create a busy loop.
- A valid frame after reopening restores pose processing and allows an automatic return to `Fusion` mode.
- The dashboard remains responsive during camera loss and displays a short status describing the active source or reconnect attempt.
- RTSP buffering is minimized where the OpenCV backend supports it.
- Cleanup always releases the capture and closes dashboard windows.

The IMU safety and rehabilitation feedback remains available throughout a camera interruption.

## Hardware Connection

No GPIO connection is required between MaixCAM 2 and either ESP32 board.

- MaixCAM 2 USB Type-C port connects to the host computer for power and UVC video.
- The ESP32-S3 receiver connects to a second host USB port for power and serial telemetry.
- The right-arm wearable remains connected to the receiver over BLE.
- In RTSP mode, MaixCAM 2 and the host use the same Wi-Fi network or the MaixCAM 2 USB virtual network adapter.

The two USB devices must use data-capable cables. A powered USB hub is acceptable if the host has insufficient ports or unstable power.

## User Workflow

1. Start the MaixCAM 2 application in UVC mode.
2. Connect both USB devices.
3. Run the camera probe to identify a working source.
4. Start the dashboard with the right-arm setting and detected camera source.
5. Confirm `Fusion` and visible right shoulder, elbow, wrist, and hip landmarks.
6. Perform the existing baseline and exercise demonstration.
7. If UVC is unavailable, start RTSP mode and launch the same dashboard with the printed RTSP URL.

## Testing

Tests are written before production behavior and cover:

- parsing local indices, `auto`, and RTSP URLs;
- rejecting unsupported or empty source values;
- successful local and RTSP capture construction;
- transition to unhealthy after repeated read failures;
- rate-limited reopen attempts;
- recovery after a valid frame;
- clean release;
- dashboard command-line compatibility.

All existing Python and C host tests must continue to pass. The dashboard headless smoke test must also pass. Because physical MaixCAM 2 hardware may not be continuously available, the capture lifecycle is tested with a controlled fake OpenCV backend; final UVC and RTSP checks are documented as hardware acceptance steps.

## Acceptance Criteria

- The dashboard starts with either a UVC camera index or an RTSP URL.
- Camera loss does not terminate the dashboard or disable serial IMU processing.
- Vision automatically recovers when frames resume.
- Existing `--camera 0` usage still works.
- The MaixCAM 2 scripts use documented MaixPy APIs and are directly runnable from MaixVision on a current MaixCAM 2 system image.
- The repository contains concise connection, launch, fallback, and demonstration instructions.
- The automated test suite passes without new warnings.

