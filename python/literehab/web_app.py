from __future__ import annotations

import asyncio
import ipaddress
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterator

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .mobile_access import MobileAccessConfig, authorization_matches
from .session_repository import SessionRepository
from .web_runtime import RuntimeProtocol


class StartSessionRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=64)

    @field_validator("subject")
    @classmethod
    def normalize_subject(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Participant ID is required")
        return normalized


def _runtime_conflict(error: RuntimeError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(error))


def _is_loopback(host: str | None) -> bool:
    if host is None or host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def camera_frames(
    runtime: RuntimeProtocol,
    first_frame: bytes,
    interval_s: float = 0.05,
) -> Iterator[bytes]:
    frame: bytes | None = first_frame
    while frame is not None:
        yield (
            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
            + frame
            + b"\r\n"
        )
        time.sleep(interval_s)
        frame = runtime.jpeg_frame()


def create_app(
    runtime: RuntimeProtocol,
    sessions_dir: Path,
    frontend_dir: Path | None = None,
    mobile_access: MobileAccessConfig | None = None,
) -> FastAPI:
    app = FastAPI(title="LiteRehab Local Dashboard", version="1.0")
    repository = SessionRepository(sessions_dir)

    @app.middleware("http")
    async def mobile_authentication(request: Request, call_next):
        protected = request.url.path == "/api" or request.url.path.startswith("/api/")
        remote = not _is_loopback(request.client.host if request.client else None)
        if mobile_access is not None and protected and remote:
            if not authorization_matches(
                mobile_access,
                request.headers.get("Authorization"),
            ):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Pairing required"},
                )
        return await call_next(request)

    @app.get("/api/status")
    def status() -> dict[str, object]:
        return runtime.snapshot().to_dict()

    @app.get("/api/mobile/health")
    def mobile_health() -> dict[str, object]:
        return {
            "service": (
                mobile_access.service_name if mobile_access else "LiteRehab Mac"
            ),
            "api_version": mobile_access.api_version if mobile_access else 1,
        }

    @app.get("/api/sessions")
    def sessions() -> list[dict[str, object]]:
        return [asdict(item) for item in repository.list_sessions()]

    @app.get("/api/sessions/{session_id}")
    def report(session_id: str) -> dict[str, object]:
        try:
            return asdict(repository.get_report(session_id))
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Session not found") from error

    @app.post("/api/session/start")
    def start_session(request: StartSessionRequest) -> dict[str, object]:
        try:
            runtime.start_session(request.subject)
        except RuntimeError as error:
            raise _runtime_conflict(error) from error
        return {"recording": runtime.recording, "subject": request.subject}

    @app.post("/api/session/stop")
    def stop_session() -> dict[str, object]:
        try:
            runtime.stop_session()
        except RuntimeError as error:
            raise _runtime_conflict(error) from error
        return {
            "recording": runtime.recording,
            "subject": runtime.snapshot().subject,
        }

    @app.post("/api/session/baseline")
    def recapture_baseline() -> dict[str, bool]:
        runtime.recapture_baseline()
        return {"ok": True}

    @app.post("/api/session/range/reset")
    def reset_range() -> dict[str, bool]:
        runtime.reset_range()
        return {"ok": True}

    @app.websocket("/api/live")
    async def live(socket: WebSocket) -> None:
        remote = not _is_loopback(socket.client.host if socket.client else None)
        if mobile_access is not None and remote and not authorization_matches(
            mobile_access,
            socket.headers.get("Authorization"),
        ):
            await socket.accept()
            await socket.close(code=4401, reason="Pairing required")
            return
        await socket.accept()
        try:
            while True:
                await socket.send_json(runtime.snapshot().to_dict())
                await asyncio.sleep(0.05)
        except WebSocketDisconnect:
            return

    @app.get("/api/camera.mjpg")
    def camera() -> StreamingResponse:
        frame = runtime.jpeg_frame()
        if frame is None:
            raise HTTPException(status_code=503, detail="Camera frame unavailable")
        return StreamingResponse(
            camera_frames(runtime, frame),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @app.get("/api/camera.jpg")
    def camera_snapshot() -> Response:
        frame = runtime.jpeg_frame()
        if frame is None:
            raise HTTPException(status_code=503, detail="Camera frame unavailable")
        return Response(
            content=frame,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-store"},
        )

    if frontend_dir is not None:
        frontend_dir = Path(frontend_dir)
        assets_dir = frontend_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def frontend(full_path: str) -> FileResponse:
            if full_path == "api" or full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API route not found")
            index = frontend_dir / "index.html"
            if not index.is_file():
                raise HTTPException(
                    status_code=503,
                    detail="Web frontend has not been built",
                )
            return FileResponse(index)

    return app
