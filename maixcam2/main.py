"""LiteRehab MaixCAM 2 video source.

Change MODE to ``"rtsp"`` only when USB UVC is unavailable.  Run this file
from MaixVision after enabling UVC in the MaixCAM 2 USB settings for UVC mode.
"""

from maix import app, camera, image, rtsp, time, uvc


MODE = "rtsp"
WIDTH = 640
HEIGHT = 480
FPS = 30


def run_uvc() -> None:
    """Send the built-in camera as a USB MJPEG UVC device."""
    cam = camera.Camera(WIDTH, HEIGHT, fps=FPS, buff_num=1)
    cam.skip_frames(10)

    def fill_mjpg_frame(buffer, size):
        frame = cam.read()
        return uvc.helper_fill_mjpg_image(buffer, size, frame)

    server = uvc.UvcServer(fill_mjpg_frame)
    server.run()

    print("LiteRehab MaixCAM 2: USB UVC/MJPEG active")
    while not app.need_exit():
        time.sleep(0.2)


def run_rtsp() -> None:
    """Serve the built-in camera as RTSP at rtsp://<device-ip>:8554/live."""
    cam = camera.Camera(
        WIDTH,
        HEIGHT,
        image.Format.FMT_YVU420SP,
        fps=FPS,
        buff_num=1,
    )
    server = rtsp.Rtsp()
    server.bind_camera(cam)
    server.start()
    print("LiteRehab MaixCAM 2 RTSP URL:", server.get_url())

    while not app.need_exit():
        time.sleep(0.2)


if MODE == "uvc":
    run_uvc()
elif MODE == "rtsp":
    run_rtsp()
else:
    raise ValueError("MODE must be 'uvc' or 'rtsp'")
