# LiteRehab MaixCAM 2 Camera

`main.py` turns MaixCAM 2 into the LiteRehab vision source. It uses the built-in camera only; it does not connect to either ESP32 GPIO.

## Recommended: RTSP over USB NCM

1. Connect MaixCAM 2 to the laptop with a Type-C **data** cable and enable its USB NCM/network function if the system image requires USB-function selection.
2. Open `main.py` in MaixVision and run its committed `MODE = "rtsp"` configuration.
3. Copy the URL printed in the MaixVision terminal, normally `rtsp://10.203.102.1:8554/live` over USB NCM.
4. In the activated LiteRehab Python environment, run:

   ```bash
   PYTHON=python ./scripts/start_maixcam2_demo.sh rtsp://10.203.102.1:8554/live
   ```

If the printed USB NCM address differs, use that exact RTSP URL. The dashboard must show `Camera: connected` and `Mode: Fusion` once the right shoulder, elbow, wrist, and hip are visible.

## Optional: USB UVC

Use UVC only when a local camera device is preferable:

1. On MaixCAM 2, enable **UVC** in **Settings → USB Settings**.
2. Run `main.py` in MaixVision with `MODE = "uvc"`.
3. Identify the MaixCAM 2 camera index and start the dashboard:

   ```bash
   PYTHONPATH=python python scripts/probe_cameras.py
   PYTHON=python ./scripts/start_maixcam2_demo.sh <maixcam-index>
   ```

## Placement

- Place MaixCAM 2 horizontally, 1.5–2.0 m from the participant, at chest height.
- Keep the whole upper body and hips in frame. For right-arm rehabilitation, keep the right shoulder, elbow, wrist, and right hip unobstructed.
- Use `b` in the focused dashboard window while standing in a neutral posture to refresh the trunk baseline.

## Official references

- [MaixCAM 2 quick start](https://wiki.sipeed.com/maixpy/doc/en/README_MaixCAM2.html)
- [MaixPy UVC streaming](https://wiki.sipeed.com/maixpy/doc/en/video/uvc_streaming.html)
- [MaixPy RTSP streaming](https://wiki.sipeed.com/maixpy/doc/zh/video/rtsp_streaming.html)
- [MaixPy camera configuration](https://wiki.sipeed.com/maixpy/doc/en/vision/camera.html)
