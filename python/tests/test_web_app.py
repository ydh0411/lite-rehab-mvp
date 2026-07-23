import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from literehab.mobile_access import MobileAccessConfig
from literehab.web_app import camera_frames, create_app
from literehab.web_runtime import FixtureRuntime


def test_api_lists_sessions_and_controls_runtime(tmp_path):
    runtime = FixtureRuntime()
    client = TestClient(create_app(runtime, tmp_path))

    assert client.get("/api/sessions").json() == []

    response = client.post("/api/session/start", json={"subject": "Demo-01"})
    assert response.status_code == 200
    assert response.json() == {"recording": True, "subject": "Demo-01"}

    response = client.post("/api/session/stop")
    assert response.status_code == 200
    assert response.json() == {"recording": False, "subject": "Demo-01"}


def test_api_maps_invalid_transition_to_conflict(tmp_path):
    runtime = FixtureRuntime()
    client = TestClient(create_app(runtime, tmp_path))

    response = client.post("/api/session/stop")

    assert response.status_code == 409
    assert response.json()["detail"] == "Session is not recording"


def test_api_validates_participant_id(tmp_path):
    client = TestClient(create_app(FixtureRuntime(), tmp_path))

    assert client.post("/api/session/start", json={"subject": ""}).status_code == 422
    assert client.post(
        "/api/session/start", json={"subject": "x" * 65}
    ).status_code == 422


def test_websocket_sends_live_snapshot(tmp_path):
    runtime = FixtureRuntime()
    client = TestClient(create_app(runtime, tmp_path))

    with client.websocket_connect("/api/live") as socket:
        payload = socket.receive_json()

    assert payload["exercise"] == "idle"
    assert payload["rom_deg"] is None
    assert payload["ecg_bpm"] is None
    assert payload["serial_status"] == "unavailable"


def test_camera_is_explicitly_unavailable_without_a_frame(tmp_path):
    client = TestClient(create_app(FixtureRuntime(), tmp_path))

    response = client.get("/api/camera.mjpg")

    assert response.status_code == 503
    assert response.json()["detail"] == "Camera frame unavailable"


def test_camera_stream_is_rate_limited(monkeypatch):
    runtime = FixtureRuntime()
    waits = []
    monkeypatch.setattr(runtime, "jpeg_frame", lambda: b"second-frame")
    monkeypatch.setattr("literehab.web_app.time.sleep", waits.append)

    stream = camera_frames(runtime, b"first-frame", interval_s=0.05)
    assert b"first-frame" in next(stream)
    assert b"second-frame" in next(stream)

    assert waits == [0.05]


def test_remote_mobile_api_requires_pairing_token(tmp_path):
    app = create_app(
        FixtureRuntime(),
        tmp_path,
        mobile_access=MobileAccessConfig("secret-token"),
    )
    client = TestClient(app, client=("192.168.1.40", 50000))

    assert client.get("/api/mobile/health").status_code == 401
    response = client.get(
        "/api/mobile/health",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "service": "LiteRehab Mac",
        "api_version": 1,
    }


def test_loopback_desktop_api_remains_unauthed(tmp_path):
    app = create_app(
        FixtureRuntime(),
        tmp_path,
        mobile_access=MobileAccessConfig("secret-token"),
    )
    client = TestClient(app, client=("127.0.0.1", 50000))

    assert client.get("/api/sessions").status_code == 200


def test_camera_snapshot_returns_latest_jpeg(monkeypatch, tmp_path):
    runtime = FixtureRuntime()
    monkeypatch.setattr(runtime, "jpeg_frame", lambda: b"jpeg-frame")
    client = TestClient(create_app(runtime, tmp_path))

    response = client.get("/api/camera.jpg")

    assert response.status_code == 200
    assert response.content == b"jpeg-frame"
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "no-store"


def test_camera_snapshot_reports_unavailable(tmp_path):
    client = TestClient(create_app(FixtureRuntime(), tmp_path))

    response = client.get("/api/camera.jpg")

    assert response.status_code == 503
    assert response.json()["detail"] == "Camera frame unavailable"


def test_remote_websocket_accepts_pairing_token(tmp_path):
    app = create_app(
        FixtureRuntime(),
        tmp_path,
        mobile_access=MobileAccessConfig("secret-token"),
    )
    client = TestClient(app, client=("192.168.1.40", 50000))

    with client.websocket_connect(
        "/api/live",
        headers={"Authorization": "Bearer secret-token"},
    ) as socket:
        assert socket.receive_json()["exercise"] == "idle"


def test_remote_websocket_rejects_missing_pairing_token(tmp_path):
    app = create_app(
        FixtureRuntime(),
        tmp_path,
        mobile_access=MobileAccessConfig("secret-token"),
    )
    client = TestClient(app, client=("192.168.1.40", 50000))

    with pytest.raises(WebSocketDisconnect) as caught:
        with client.websocket_connect("/api/live") as socket:
            socket.receive_json()

    assert caught.value.code == 4401


def test_unknown_report_returns_not_found(tmp_path):
    client = TestClient(create_app(FixtureRuntime(), tmp_path))

    response = client.get("/api/sessions/missing")

    assert response.status_code == 404


def test_built_frontend_falls_back_to_spa_routes(tmp_path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text("<main>LiteRehab local app</main>")
    client = TestClient(create_app(FixtureRuntime(), tmp_path, frontend))

    response = client.get("/history")

    assert response.status_code == 200
    assert "LiteRehab local app" in response.text


def test_unknown_api_route_never_returns_frontend(tmp_path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text("<main>LiteRehab local app</main>")
    client = TestClient(create_app(FixtureRuntime(), tmp_path, frontend))

    response = client.get("/api/unknown")

    assert response.status_code == 404
