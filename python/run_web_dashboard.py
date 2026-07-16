#!/usr/bin/env python3
from __future__ import annotations

import argparse
import threading
import webbrowser
from pathlib import Path

import uvicorn
from fastapi.testclient import TestClient

from literehab.camera_source import parse_camera_source
from literehab.web_app import create_app
from literehab.web_runtime import FixtureRuntime, LiteRehabRuntime, RuntimeConfig


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = Path(__file__).resolve().parent / "models" / "imu_cnnbigru.pt"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LiteRehab offline local web dashboard",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--web-port", type=int, default=8000)
    parser.add_argument("--port", default="auto", help="ESP32-S3 serial port")
    parser.add_argument(
        "--camera-source",
        default="auto",
        help="auto, a non-negative UVC index, or an rtsp:// URL",
    )
    parser.add_argument("--side", choices=["left", "right"], default="right")
    parser.add_argument(
        "--sessions-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "sessions",
    )
    parser.add_argument(
        "--frontend-dir",
        type=Path,
        default=PROJECT_ROOT / "web" / "dist",
    )
    parser.add_argument(
        "--model",
        default=str(DEFAULT_MODEL),
        help="IMU checkpoint path, or 'none' to disable it",
    )
    parser.add_argument("--fusion-model", type=Path)
    parser.add_argument("--model-confidence", type=float, default=0.70)
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--headless-smoke-test", action="store_true")
    return parser


def config_from_args(args: argparse.Namespace) -> RuntimeConfig:
    try:
        camera_source = parse_camera_source(args.camera_source)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    model = None if str(args.model).lower() == "none" else Path(args.model)
    return RuntimeConfig(
        port=args.port,
        camera_source=camera_source,
        side=args.side,
        sessions_dir=args.sessions_dir,
        model=model,
        fusion_model=args.fusion_model,
        model_confidence=args.model_confidence,
    )


def main() -> None:
    args = build_parser().parse_args()
    if not 1 <= args.web_port <= 65535:
        raise SystemExit("--web-port must be between 1 and 65535")
    config = config_from_args(args)
    runtime = FixtureRuntime() if args.fixture else LiteRehabRuntime(config)
    runtime.start()
    app = create_app(runtime, config.sessions_dir, args.frontend_dir)

    if args.headless_smoke_test:
        try:
            response = TestClient(app).get("/api/status")
            response.raise_for_status()
            print("LiteRehab web dashboard smoke test: PASS")
        finally:
            runtime.close()
        return

    url = f"http://{args.host}:{args.web_port}"
    if not args.no_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        uvicorn.run(app, host=args.host, port=args.web_port, log_level="info")
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
