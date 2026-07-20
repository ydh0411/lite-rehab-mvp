# LiteRehab Native iPhone App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an installable portrait iPhone app that pairs with the existing Mac runtime and provides native Live Training, Session History, and Session Report experiences.

**Architecture:** Keep FastAPI and the hardware runtime as the source of truth, adding an opt-in authenticated LAN mode and bounded JPEG endpoint. Build the iPhone UI in SwiftUI on a minimal Stanford Spezi application shell, with a Foundation-only `LiteRehabCore` Swift package so contracts and validation can be tested before full Xcode is available.

**Tech Stack:** Python 3.12, FastAPI 0.116, qrcode 8.x, Swift 6, SwiftUI, Charts, AVFoundation, PDFKit/UIKit PDF rendering, Stanford Spezi 1.10.2, SpeziViews 1.12.14, XcodeGen, XCTest/Swift Testing.

## Global Constraints

- Target iPhone in portrait orientation on iOS 17 or later.
- Keep the interface English-only in the first release.
- Install directly from Xcode; do not add App Store, TestFlight, cloud accounts, or cloud storage.
- Keep Python, ESP32, ECG, MaixCAM2, pose processing, model inference, CSV recording, and report calculations on the Mac.
- Store only the endpoint label/address in `UserDefaults` and the pairing token in Keychain.
- Require the Mac and iPhone to share a trusted local network; loopback remains the backend default.
- Do not add HealthKit, direct ESP32 BLE, direct MaixCAM2 access, or Core ML to this release.
- Preserve the existing desktop web app and all current API shapes unless this plan explicitly adds an endpoint.
- Keep the engineering-prototype and non-medical disclaimer visible in Report and Settings.
- Retain required MIT/BSD notices; do not imply Apple or Stanford endorsement.
- Full Xcode 16.3 or later is a verification prerequisite. The current machine has Command Line Tools only, so install Xcode before Tasks 6-12 are finally verified.

---

## Planned File Structure

```text
ios/
├── project.yml                         # XcodeGen source of truth
├── LiteRehabCore/
│   ├── Package.swift                   # Foundation-only reusable/testable core
│   ├── Sources/LiteRehabCore/
│   │   ├── APIModels.swift             # Codable parity with FastAPI
│   │   ├── Pairing.swift               # QR payload and validation
│   │   ├── RequestFactory.swift         # Authenticated REST/WS request construction
│   │   ├── HistoryFilter.swift          # Search/filter behavior
│   │   └── ReportFormatting.swift       # Missing values and display formatting
│   └── Tests/LiteRehabCoreTests/        # Core contract tests
├── LiteRehab/
│   ├── App/                             # Spezi lifecycle and root routing
│   ├── Pairing/                         # QR scanner, Keychain, pairing UI
│   ├── Networking/                      # URLSession, WebSocket, camera clients
│   ├── Live/                            # Live store and native training UI
│   ├── History/                         # History store and card list
│   ├── Report/                          # Charts, warnings, PDF sharing
│   ├── Settings/                        # Connection, disclaimer, notices
│   ├── DesignSystem/                    # Shared styles/components
│   └── Resources/                       # Info.plist, assets, notices
├── LiteRehabTests/                      # App-layer unit tests
└── LiteRehabUITests/                    # Pairing/navigation UI tests
```

The Mac additions stay focused in `python/literehab/mobile_access.py`; HTTP wiring remains in `web_app.py`, and CLI startup remains in `run_web_dashboard.py`.

---

### Task 1: Mobile Access Configuration and Pairing Payload

**Files:**
- Create: `python/literehab/mobile_access.py`
- Create: `python/tests/test_mobile_access.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `MobileAccessConfig`, `load_or_create_token(path: Path) -> str`, `create_pairing_payload(...) -> dict[str, object]`, `detect_lan_ip() -> str`, and `authorization_matches(config, header) -> bool`.
- Consumes: Python standard library only.

- [ ] **Step 1: Write failing token, payload, and authorization tests**

```python
from pathlib import Path

import pytest

from literehab.mobile_access import (
    MobileAccessConfig,
    authorization_matches,
    create_pairing_payload,
    load_or_create_token,
)


def test_token_is_persistent_and_private(tmp_path: Path):
    path = tmp_path / "mobile-token"
    first = load_or_create_token(path)
    second = load_or_create_token(path)
    assert first == second
    assert len(first) >= 32
    assert path.stat().st_mode & 0o777 == 0o600


def test_pairing_payload_is_versioned():
    config = MobileAccessConfig(token="secret-token", api_version=1)
    assert create_pairing_payload(config, "192.168.1.8", 8000) == {
        "version": 1,
        "name": "LiteRehab Mac",
        "base_url": "http://192.168.1.8:8000",
        "pairing_token": "secret-token",
    }


@pytest.mark.parametrize("header", [None, "", "Basic secret-token", "Bearer wrong"])
def test_authorization_rejects_invalid_headers(header):
    assert not authorization_matches(MobileAccessConfig("secret-token"), header)


def test_authorization_accepts_matching_bearer_token():
    assert authorization_matches(
        MobileAccessConfig("secret-token"), "Bearer secret-token"
    )
```

- [ ] **Step 2: Run the test and verify the missing module failure**

Run: `PYTHONPATH=python python -m pytest python/tests/test_mobile_access.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'literehab.mobile_access'`.

- [ ] **Step 3: Implement the immutable mobile configuration and helpers**

```python
from __future__ import annotations

import secrets
import socket
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MobileAccessConfig:
    token: str
    api_version: int = 1
    service_name: str = "LiteRehab Mac"


def load_or_create_token(path: Path) -> str:
    if path.is_file():
        token = path.read_text(encoding="utf-8").strip()
        if token:
            path.chmod(0o600)
            return token
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    path.write_text(token + "\n", encoding="utf-8")
    path.chmod(0o600)
    return token


def create_pairing_payload(
    config: MobileAccessConfig, host: str, port: int
) -> dict[str, object]:
    return {
        "version": config.api_version,
        "name": config.service_name,
        "base_url": f"http://{host}:{port}",
        "pairing_token": config.token,
    }


def authorization_matches(config: MobileAccessConfig, header: str | None) -> bool:
    prefix = "Bearer "
    if header is None or not header.startswith(prefix):
        return False
    return secrets.compare_digest(config.token, header[len(prefix):])


def detect_lan_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect(("192.0.2.1", 80))
        return str(probe.getsockname()[0])
```

Add `python/.literehab_mobile_token` and `python/.literehab_pairing.png` to `.gitignore`.

- [ ] **Step 4: Run focused tests**

Run: `PYTHONPATH=python python -m pytest python/tests/test_mobile_access.py -q`

Expected: all tests PASS.

- [ ] **Step 5: Commit the mobile configuration unit**

```bash
git add .gitignore python/literehab/mobile_access.py python/tests/test_mobile_access.py
git commit -m "feat: add secure mobile pairing configuration"
```

---

### Task 2: Authenticated Mobile FastAPI Surface

**Files:**
- Modify: `python/literehab/web_app.py`
- Modify: `python/tests/test_web_app.py`

**Interfaces:**
- Consumes: `MobileAccessConfig` and `authorization_matches` from Task 1.
- Produces: `create_app(..., mobile_access: MobileAccessConfig | None = None)`, `GET /api/mobile/health`, and `GET /api/camera.jpg`.

- [ ] **Step 1: Add failing tests for remote authentication, health, camera JPEG, and loopback compatibility**

```python
from literehab.mobile_access import MobileAccessConfig


def test_remote_mobile_api_requires_pairing_token(tmp_path):
    app = create_app(
        FixtureRuntime(), tmp_path,
        mobile_access=MobileAccessConfig("secret-token"),
    )
    client = TestClient(app, client=("192.168.1.40", 50000))
    assert client.get("/api/mobile/health").status_code == 401
    response = client.get(
        "/api/mobile/health",
        headers={"Authorization": "Bearer secret-token"},
    )
    assert response.json() == {
        "service": "LiteRehab Mac",
        "api_version": 1,
    }


def test_loopback_desktop_api_remains_unauthed(tmp_path):
    app = create_app(
        FixtureRuntime(), tmp_path,
        mobile_access=MobileAccessConfig("secret-token"),
    )
    client = TestClient(app, client=("127.0.0.1", 50000))
    assert client.get("/api/sessions").status_code == 200


def test_camera_snapshot_returns_latest_jpeg(tmp_path):
    runtime = FixtureRuntime()
    runtime.jpeg_frame = lambda: b"jpeg-frame"
    client = TestClient(create_app(runtime, tmp_path))
    response = client.get("/api/camera.jpg")
    assert response.status_code == 200
    assert response.content == b"jpeg-frame"
    assert response.headers["cache-control"] == "no-store"
```

Add these authenticated and rejected WebSocket cases:

```python
from starlette.websockets import WebSocketDisconnect


def test_remote_websocket_accepts_pairing_token(tmp_path):
    app = create_app(
        FixtureRuntime(), tmp_path,
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
        FixtureRuntime(), tmp_path,
        mobile_access=MobileAccessConfig("secret-token"),
    )
    client = TestClient(app, client=("192.168.1.40", 50000))
    with pytest.raises(WebSocketDisconnect) as caught:
        with client.websocket_connect("/api/live") as socket:
            socket.receive_json()
    assert caught.value.code == 4401
```

- [ ] **Step 2: Run the focused web tests**

Run: `PYTHONPATH=python python -m pytest python/tests/test_web_app.py -q`

Expected: FAIL because `create_app` does not accept `mobile_access` and the new routes do not exist.

- [ ] **Step 3: Add loopback-aware middleware and mobile routes**

Implement these exact rules in `create_app`:

```python
def _is_loopback(host: str | None) -> bool:
    return host in {"127.0.0.1", "::1", "localhost", None}


@app.middleware("http")
async def mobile_authentication(request: Request, call_next):
    protected = request.url.path == "/api" or request.url.path.startswith("/api/")
    remote = not _is_loopback(request.client.host if request.client else None)
    if mobile_access is not None and protected and remote:
        if not authorization_matches(mobile_access, request.headers.get("Authorization")):
            return JSONResponse(status_code=401, content={"detail": "Pairing required"})
    return await call_next(request)


@app.get("/api/mobile/health")
def mobile_health() -> dict[str, object]:
    return {
        "service": mobile_access.service_name if mobile_access else "LiteRehab Mac",
        "api_version": mobile_access.api_version if mobile_access else 1,
    }


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
```

Before accepting `/api/live`, apply the same remote/token rule to `socket.client.host` and `socket.headers.get("Authorization")`; close with `4401` on failure.

- [ ] **Step 4: Run mobile and regression tests**

Run: `PYTHONPATH=python python -m pytest python/tests/test_web_app.py python/tests/test_web_runtime.py python/tests/test_real_web_runtime.py -q`

Expected: all tests PASS, including original unauthenticated loopback tests.

- [ ] **Step 5: Commit the authenticated API surface**

```bash
git add python/literehab/web_app.py python/tests/test_web_app.py
git commit -m "feat: expose authenticated mobile dashboard API"
```

---

### Task 3: Mobile CLI Mode and QR Startup

**Files:**
- Modify: `python/requirements.txt`
- Modify: `python/run_web_dashboard.py`
- Modify: `python/tests/test_web_dashboard_cli.py`
- Create: `scripts/start_ios_demo.sh`

**Interfaces:**
- Consumes: Task 1 pairing helpers and Task 2 `create_app` parameter.
- Produces: CLI flags `--mobile`, `--advertised-host`, and `--mobile-token-file`; `mobile_access_from_args(args) -> tuple[MobileAccessConfig | None, dict[str, object] | None]`; terminal QR display; one-command iPhone demo startup.

- [ ] **Step 1: Add failing parser/configuration tests**

```python
def test_mobile_cli_defaults_to_persistent_token(tmp_path):
    args = build_parser().parse_args([
        "--mobile",
        "--advertised-host", "192.168.1.8",
        "--mobile-token-file", str(tmp_path / "token"),
    ])
    assert args.mobile is True
    assert args.advertised_host == "192.168.1.8"
    assert args.mobile_token_file == tmp_path / "token"
```

Add these rejection and regression cases:

```python
def test_mobile_mode_rejects_loopback_binding():
    args = build_parser().parse_args(["--mobile", "--host", "127.0.0.1"])
    with pytest.raises(SystemExit, match="mobile mode requires a LAN bind address"):
        mobile_access_from_args(args)


def test_desktop_cli_defaults_remain_loopback_only():
    args = build_parser().parse_args([])
    assert args.host == "127.0.0.1"
    assert args.mobile is False
```

- [ ] **Step 2: Run the CLI tests**

Run: `PYTHONPATH=python python -m pytest python/tests/test_web_dashboard_cli.py -q`

Expected: FAIL because the mobile arguments do not exist.

- [ ] **Step 3: Implement CLI wiring and QR output**

Add `qrcode>=8,<9` to requirements. Add these parser arguments:

```python
parser.add_argument("--mobile", action="store_true")
parser.add_argument("--advertised-host")
parser.add_argument(
    "--mobile-token-file",
    type=Path,
    default=Path(__file__).resolve().parent / ".literehab_mobile_token",
)
```

When `--mobile` is set:

1. require `--host 0.0.0.0` or a non-loopback bind address;
2. load the persistent token;
3. choose `--advertised-host` or `detect_lan_ip()`;
4. create the payload and pass `MobileAccessConfig` to `create_app`;
5. encode compact JSON with `json.dumps(payload, separators=(",", ":"))`;
6. call `qrcode.QRCode(border=2).print_ascii(invert=True)`; and
7. print the advertised URL without printing the token separately.

Create `scripts/start_ios_demo.sh` following the existing script style:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAMERA_SOURCE="${1:-auto}"
PYTHON_BIN="${PYTHON:-python}"

export PYTHONPATH="$ROOT/python${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON_BIN" "$ROOT/python/run_web_dashboard.py" \
  --host 0.0.0.0 \
  --mobile \
  --no-browser \
  --camera-source "$CAMERA_SOURCE"
```

- [ ] **Step 4: Verify fixture mobile startup and regression suite**

Run: `PYTHONPATH=python python -m pytest python/tests/test_mobile_access.py python/tests/test_web_app.py python/tests/test_web_dashboard_cli.py -q`

Then run: `PYTHONPATH=python python python/run_web_dashboard.py --fixture --mobile --host 0.0.0.0 --advertised-host 127.0.0.1 --no-browser`

Expected: tests PASS; manual command prints a QR and starts Uvicorn. Stop it with `Ctrl+C` after inspection.

- [ ] **Step 5: Commit mobile startup**

```bash
git add python/requirements.txt python/run_web_dashboard.py \
  python/tests/test_web_dashboard_cli.py scripts/start_ios_demo.sh
git commit -m "feat: start mobile dashboard with QR pairing"
```

---

### Task 4: Swift Core Package and API Contracts

**Files:**
- Create: `ios/LiteRehabCore/Package.swift`
- Create: `ios/LiteRehabCore/Sources/LiteRehabCore/APIModels.swift`
- Create: `ios/LiteRehabCore/Sources/LiteRehabCore/Pairing.swift`
- Create: `ios/LiteRehabCore/Tests/LiteRehabCoreTests/APIModelsTests.swift`
- Create: `ios/LiteRehabCore/Tests/LiteRehabCoreTests/PairingTests.swift`

**Interfaces:**
- Produces: public `LiveSnapshot`, `SessionSummary`, `SessionReport`, `SeriesPoint`, `PairingPayload`, `ServerConnection`, and `PairingValidationError`.
- Consumes: exact JSON shapes from `web/src/app/api.ts` and Task 1's QR payload.

- [ ] **Step 1: Create the Swift package manifest and failing decoding tests**

```swift
// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "LiteRehabCore",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [.library(name: "LiteRehabCore", targets: ["LiteRehabCore"])],
    targets: [
        .target(name: "LiteRehabCore"),
        .testTarget(name: "LiteRehabCoreTests", dependencies: ["LiteRehabCore"]),
    ]
)
```

Use these concrete fixtures and assertions:

```swift
@Test func decodesLiveSnapshotFromFastAPIShape() throws {
    let data = #"{"timestamp_s":1.0,"recording":false,"subject":"","exercise":"idle","repetitions":0,"feedback":"Ready","mode":"IMU-only","source":"rule fallback","side":"right","serial_status":"unavailable","camera_status":"unavailable","rom_deg":null,"confidence_text":"Model unavailable","model_confidence":null,"ecg_bpm":null,"ecg_connected":true,"ecg_samples":[101,102],"camera_frame_age_s":null}"#.data(using: .utf8)!
    let value = try JSONDecoder.liteRehab.decode(LiveSnapshot.self, from: data)
    #expect(value.romDeg == nil)
    #expect(value.ecgSamples == [101, 102])
}

@Test func validatesOnlyVersionedLocalPairingPayloads() throws {
    let valid = PairingPayload(
        version: 1,
        name: "LiteRehab Mac",
        baseURL: URL(string: "http://192.168.1.8:8000")!,
        pairingToken: "secret-token"
    )
    #expect(try valid.validated().token == "secret-token")
    #expect(throws: PairingValidationError.unsupportedVersion) {
        _ = try PairingPayload(
            version: 2, name: valid.name,
            baseURL: valid.baseURL, pairingToken: valid.pairingToken
        ).validated()
    }
    #expect(throws: PairingValidationError.nonLocalHost) {
        _ = try PairingPayload(
            version: 1, name: valid.name,
            baseURL: URL(string: "https://example.com")!,
            pairingToken: valid.pairingToken
        ).validated()
    }
    #expect(throws: PairingValidationError.missingToken) {
        _ = try PairingPayload(
            version: 1, name: valid.name,
            baseURL: valid.baseURL, pairingToken: ""
        ).validated()
    }
}
```

- [ ] **Step 2: Run Swift tests and verify missing-type failures**

Run: `cd ios/LiteRehabCore && swift test`

Expected: FAIL because the model types do not exist.

- [ ] **Step 3: Implement Codable models and pairing validation**

Use immutable `Sendable`, `Equatable`, `Codable` structs. Configure one shared decoder:

```swift
public extension JSONDecoder {
    static var liteRehab: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }
}
```

`PairingPayload.validated()` must:

- require `version == 1`;
- require `http` or `https`;
- require a non-empty token;
- accept `localhost`, `.local`, IPv4 private ranges, and IPv6 local/link-local hosts; and
- return `ServerConnection(name:baseURL:token:)`.

- [ ] **Step 4: Run Swift core tests**

Run: `cd ios/LiteRehabCore && swift test`

Expected: all tests PASS under the installed command-line Swift toolchain.

- [ ] **Step 5: Commit the cross-platform contracts**

```bash
git add ios/LiteRehabCore
git commit -m "feat: add iPhone API contract package"
```

---

### Task 5: Swift Request Construction, History Filtering, and Formatting

**Files:**
- Create: `ios/LiteRehabCore/Sources/LiteRehabCore/RequestFactory.swift`
- Create: `ios/LiteRehabCore/Sources/LiteRehabCore/HistoryFilter.swift`
- Create: `ios/LiteRehabCore/Sources/LiteRehabCore/ReportFormatting.swift`
- Create: `ios/LiteRehabCore/Tests/LiteRehabCoreTests/RequestFactoryTests.swift`
- Create: `ios/LiteRehabCore/Tests/LiteRehabCoreTests/HistoryFilterTests.swift`
- Create: `ios/LiteRehabCore/Tests/LiteRehabCoreTests/ReportFormattingTests.swift`

**Interfaces:**
- Consumes: `ServerConnection`, `SessionSummary`, and report model types from Task 4.
- Produces: `APIEndpoint`, `RequestFactory`, `filterSessions(_:query:exercise:)`, and explicit missing-value formatters.

- [ ] **Step 1: Write failing behavior tests**

Test these exact outcomes:

```swift
let request = try RequestFactory(connection: connection).request(for: .sessions)
#expect(request.url?.absoluteString == "http://192.168.1.8:8000/api/sessions")
#expect(request.value(forHTTPHeaderField: "Authorization") == "Bearer secret-token")

let filtered = filterSessions([older, newer], query: "demo-02", exercise: nil)
#expect(filtered.map(\.sessionID) == ["newer"])

#expect(ReportFormatting.percent(nil) == "Not available")
#expect(ReportFormatting.ecgCompleteness(nil) == "Not recorded")
```

Also test URL encoding of a session ID, start-session JSON body, and newest-first ordering.

- [ ] **Step 2: Run tests and verify missing-symbol failures**

Run: `cd ios/LiteRehabCore && swift test`

Expected: FAIL for missing factory/filter/formatter symbols.

- [ ] **Step 3: Implement minimal public helpers**

`APIEndpoint` must cover health, status, sessions, report, start, stop, baseline, range reset, live WebSocket, and camera JPEG. `RequestFactory` always supplies Bearer authorization, sets JSON content type for commands, and converts `http/https` to `ws/wss` only for the live endpoint.

`filterSessions` searches `subject` and `sessionID` case-insensitively, filters exact exercise values, and sorts `startedAt` descending. Formatting helpers use `—` only for decorative live metrics and use the explicit report strings required by the spec.

- [ ] **Step 4: Run all core tests**

Run: `cd ios/LiteRehabCore && swift test`

Expected: all tests PASS.

- [ ] **Step 5: Commit reusable mobile logic**

```bash
git add ios/LiteRehabCore
git commit -m "feat: add authenticated requests and report formatting"
```

---

### Task 6: XcodeGen Project, Spezi Shell, and Pairing Persistence

**Files:**
- Create: `ios/project.yml`
- Create: `ios/LiteRehab/App/LiteRehabApp.swift`
- Create: `ios/LiteRehab/App/LiteRehabAppDelegate.swift`
- Create: `ios/LiteRehab/App/AppRootView.swift`
- Create: `ios/LiteRehab/Pairing/ConnectionVault.swift`
- Create: `ios/LiteRehab/Pairing/PairingCoordinator.swift`
- Create: `ios/LiteRehab/Pairing/PairingView.swift`
- Create: `ios/LiteRehab/Pairing/QRCodeScannerView.swift`
- Create: `ios/LiteRehab/Resources/Info.plist`
- Create: `ios/LiteRehab/Resources/Assets.xcassets/Contents.json`
- Create: `ios/LiteRehabTests/ConnectionVaultTests.swift`

**Interfaces:**
- Consumes: Spezi 1.10.2, SpeziViews 1.12.14, and `LiteRehabCore`.
- Produces: generated `ios/LiteRehab.xcodeproj`, `ConnectionVault`, `PairingCoordinator`, and root paired/unpaired routing.

- [ ] **Step 1: Install/generate project tooling and write failing vault tests**

Run: `command -v xcodegen >/dev/null || brew install xcodegen`

Create `project.yml` with this deterministic structure:

```yaml
name: LiteRehab
options:
  minimumXcodeGenVersion: 2.44.1
  deploymentTarget:
    iOS: "17.0"
packages:
  LiteRehabCore:
    path: LiteRehabCore
  Spezi:
    url: https://github.com/StanfordSpezi/Spezi.git
    exactVersion: 1.10.2
  SpeziViews:
    url: https://github.com/StanfordSpezi/SpeziViews.git
    exactVersion: 1.12.14
settings:
  base:
    SWIFT_VERSION: 6.0
    DEVELOPMENT_LANGUAGE: en
targets:
  LiteRehab:
    type: application
    platform: iOS
    sources:
      - path: LiteRehab
    info:
      path: LiteRehab/Resources/Info.plist
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: edu.cuhk.literehab
        PRODUCT_NAME: LiteRehab
        MARKETING_VERSION: 0.1.0
        CURRENT_PROJECT_VERSION: 1
    dependencies:
      - package: LiteRehabCore
      - package: Spezi
      - package: SpeziViews
  LiteRehabTests:
    type: bundle.unit-test
    platform: iOS
    sources: [LiteRehabTests]
    dependencies:
      - target: LiteRehab
  LiteRehabUITests:
    type: bundle.ui-testing
    platform: iOS
    sources: [LiteRehabUITests]
    dependencies:
      - target: LiteRehab
schemes:
  LiteRehab:
    build:
      targets:
        LiteRehab: all
        LiteRehabTests: [test]
        LiteRehabUITests: [test]
    test:
      gatherCoverageData: true
      targets:
        - LiteRehabTests
        - LiteRehabUITests
```

Set the display name `LiteRehab`, keep resources under `LiteRehab/Resources`, and use iOS 17-compatible `.tabItem` APIs even though the newest upstream Spezi template demonstrates newer `Tab` syntax.

Write tests against injected `UserDefaults` and a `TokenStoring` fake asserting save, load, and clear keep the token out of defaults.

- [ ] **Step 2: Generate the project and verify tests fail for missing persistence**

Run: `cd ios && xcodegen generate`

Then, after full Xcode is installed: `xcodebuild -project LiteRehab.xcodeproj -scheme LiteRehab -destination 'platform=iOS Simulator,name=iPhone 16,OS=latest' test`

Expected: project generation succeeds; tests fail until `ConnectionVault` exists.

- [ ] **Step 3: Implement the minimal Spezi app and pairing flow**

Use this lifecycle pattern:

```swift
@main
struct LiteRehabApp: App {
    @UIApplicationDelegateAdaptor(LiteRehabAppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            AppRootView()
                .spezi(appDelegate)
        }
    }
}

final class LiteRehabAppDelegate: SpeziAppDelegate {
    override var configuration: Configuration { Configuration {} }
}
```

Implement QR scanning with `AVCaptureMetadataOutput` restricted to `.qr`. The scanner passes decoded UTF-8 JSON to `PairingPayload`, validates it, calls `/api/mobile/health`, and saves only after a successful API-version response. Use SpeziViews `ViewState` and `.viewStateAlert(state:)` for processing and error feedback.

The Info.plist must contain:

- `NSCameraUsageDescription`: “LiteRehab scans the QR code shown by your Mac to connect the app.”
- `NSLocalNetworkUsageDescription`: “LiteRehab connects to the local Mac running the rehabilitation demo.”
- a scoped `NSAppTransportSecurity` local-network allowance rather than arbitrary loads; and
- portrait-only supported orientation.

- [ ] **Step 4: Verify core tests, generated project, and paired/unpaired previews**

Run: `cd ios/LiteRehabCore && swift test`

Run after Xcode install: `cd ios && xcodegen generate && xcodebuild -project LiteRehab.xcodeproj -scheme LiteRehab -destination 'platform=iOS Simulator,name=iPhone 16,OS=latest' test`

Expected: core and vault tests PASS; simulator opens Pairing when empty and AppRoot when a fixture connection is injected.

- [ ] **Step 5: Commit the native application foundation**

```bash
git add ios/project.yml ios/LiteRehab ios/LiteRehabTests ios/LiteRehab.xcodeproj
git commit -m "feat: scaffold native Spezi iPhone app"
```

---

### Task 7: REST, WebSocket, and Camera Services

**Files:**
- Create: `ios/LiteRehab/Networking/APIClient.swift`
- Create: `ios/LiteRehab/Networking/LiveWebSocketClient.swift`
- Create: `ios/LiteRehab/Networking/CameraFrameClient.swift`
- Create: `ios/LiteRehab/Networking/NetworkError.swift`
- Create: `ios/LiteRehabTests/APIClientTests.swift`
- Create: `ios/LiteRehabTests/LiveWebSocketClientTests.swift`

**Interfaces:**
- Consumes: Task 5 request factory and Task 6 saved connection.
- Produces: `APIClientProtocol`, `LiveStreaming`, `CameraFrameLoading`, production clients, and injectable test doubles.

- [ ] **Step 1: Write URLProtocol-backed failing tests**

Test that:

- health and sessions decode with `.convertFromSnakeCase`;
- 401 maps to `.pairingExpired`;
- 409 preserves the backend detail;
- camera responses require an image MIME type;
- canceling the camera task stops polling; and
- WebSocket state follows connecting → connected → reconnecting and uses bounded delays of 1, 2, 4, 8 seconds.

- [ ] **Step 2: Run app tests and verify missing-client failures**

Run after Xcode install: `cd ios && xcodebuild -project LiteRehab.xcodeproj -scheme LiteRehab -destination 'platform=iOS Simulator,name=iPhone 16,OS=latest' test`

Expected: FAIL for missing networking types.

- [ ] **Step 3: Implement actor-isolated clients**

`APIClient` is an actor wrapping injected `URLSession`. `LiveWebSocketClient` uses `URLSessionWebSocketTask`, decodes one snapshot per message, reports state on the main actor, ignores one malformed message, and stops with `.incompatibleData` after three consecutive decode failures. Authentication failure never retries. `CameraFrameClient` requests `/api/camera.jpg` at 8 frames per second only while Live is visible and discards overlapping requests.

- [ ] **Step 4: Run networking tests**

Run after Xcode install: `cd ios && xcodebuild -project LiteRehab.xcodeproj -scheme LiteRehab -destination 'platform=iOS Simulator,name=iPhone 16,OS=latest' test`

Expected: all networking tests PASS with no real network access.

- [ ] **Step 5: Commit native transport services**

```bash
git add ios/LiteRehab/Networking ios/LiteRehabTests
git commit -m "feat: connect iPhone app to LiteRehab runtime"
```

---

### Task 8: Native Live Training Page

**Files:**
- Create: `ios/LiteRehab/DesignSystem/LiteRehabStyle.swift`
- Create: `ios/LiteRehab/DesignSystem/StatusBadge.swift`
- Create: `ios/LiteRehab/DesignSystem/MetricCard.swift`
- Create: `ios/LiteRehab/Live/LiveStore.swift`
- Create: `ios/LiteRehab/Live/LiveView.swift`
- Create: `ios/LiteRehab/Live/ECGTraceView.swift`
- Create: `ios/LiteRehab/Live/StartSessionSheet.swift`
- Create: `ios/LiteRehabTests/LiveStoreTests.swift`

**Interfaces:**
- Consumes: Task 7 service protocols and `LiveSnapshot`.
- Produces: `LiveStore` and the first tab's full portrait experience.

- [ ] **Step 1: Write failing LiveStore command/state tests**

Test that Start trims Participant ID, rejects empty/over-64-character IDs, serializes duplicate taps, disables commands when reconnecting, keeps the last snapshot marked stale, and allows camera failure without changing IMU/ECG state.

- [ ] **Step 2: Run app tests and verify missing LiveStore failure**

Run after Xcode install: `cd ios && xcodebuild -project LiteRehab.xcodeproj -scheme LiteRehab -destination 'platform=iOS Simulator,name=iPhone 16,OS=latest' test`

Expected: FAIL because `LiveStore` is missing.

- [ ] **Step 3: Implement store and portrait page**

Use the approved order: statuses, 16:9 camera, feedback banner, repetition count, ROM/exercise/side/model metrics, ECG, secondary baseline/range actions, and a safe-area Start/Stop button. Draw ECG with `Canvas`, normalize samples within the visible buffer, and show “Demonstration only.” Use native confirmation before Stop and a sheet for Participant ID.

- [ ] **Step 4: Run tests and inspect fixture preview**

Run app tests, then run the app with injected fixture services. Verify Dynamic Type at accessibility size, 44-point controls, camera-unavailable placeholder, and no clipped Stop button on an iPhone SE-sized simulator.

Expected: LiveStore tests PASS and the portrait page remains scrollable without overlapping the safe-area control.

- [ ] **Step 5: Commit Live Training**

```bash
git add ios/LiteRehab/DesignSystem ios/LiteRehab/Live ios/LiteRehabTests
git commit -m "feat: add native live training experience"
```

---

### Task 9: Native Session History

**Files:**
- Create: `ios/LiteRehab/History/HistoryStore.swift`
- Create: `ios/LiteRehab/History/HistoryView.swift`
- Create: `ios/LiteRehab/History/SessionCard.swift`
- Create: `ios/LiteRehabTests/HistoryStoreTests.swift`
- Modify: `ios/LiteRehab/App/AppRootView.swift`

**Interfaces:**
- Consumes: `APIClientProtocol`, `filterSessions`, and `SessionSummary`.
- Produces: History tab, local search/filter, pull-to-refresh, and report navigation value.

- [ ] **Step 1: Write failing HistoryStore tests**

Test initial load, refresh replacement, failure with retry, summary totals, case-insensitive Participant ID search, exact exercise filtering, and newest-first cards.

- [ ] **Step 2: Run tests and verify missing store failure**

Run the app test command.

Expected: FAIL because HistoryStore and views are missing.

- [ ] **Step 3: Implement History cards and navigation**

Use `NavigationStack`, `.searchable`, a native exercise `Picker`, `.refreshable`, overview metrics, and vertically scrolling cards. Distinguish loading, no sessions, no filtered results, disconnected, and request failure. Each card shows all existing summary fields and pushes its session ID.

Update AppRootView to use a classic iOS 17 `TabView` with `.tabItem` for Live and History rather than newer iOS-only `Tab` APIs from the current Spezi template.

- [ ] **Step 4: Run tests and UI inspection**

Run app tests and open fixture History with zero, one, and twenty sessions.

Expected: tests PASS; card list scrolls smoothly and report disclosure is VoiceOver-labeled.

- [ ] **Step 5: Commit Session History**

```bash
git add ios/LiteRehab/History ios/LiteRehab/App/AppRootView.swift ios/LiteRehabTests
git commit -m "feat: add native session history"
```

---

### Task 10: Native Session Report and PDF Sharing

**Files:**
- Create: `ios/LiteRehab/Report/ReportStore.swift`
- Create: `ios/LiteRehab/Report/ReportView.swift`
- Create: `ios/LiteRehab/Report/ReportChartsView.swift`
- Create: `ios/LiteRehab/Report/ReportPDFRenderer.swift`
- Create: `ios/LiteRehabTests/ReportStoreTests.swift`
- Create: `ios/LiteRehabTests/ReportPDFRendererTests.swift`

**Interfaces:**
- Consumes: `APIClientProtocol`, `SessionReport`, and Task 5 formatters.
- Produces: report destination and `render(report:) throws -> Data` PDF output.

- [ ] **Step 1: Write failing report and PDF tests**

Test load/success/retry states, explicit missing labels, warning preservation, metric series order, and that PDF bytes begin with `%PDF` and contain at least one page.

- [ ] **Step 2: Run tests and verify missing report types**

Run the app test command.

Expected: FAIL for missing ReportStore/renderer.

- [ ] **Step 3: Implement native metrics, Charts, quality, and PDF**

Use four metric cards, three Swift Charts line charts, quality counts, completeness badges, warning list, and the exact non-medical disclaimer. `ReportPDFRenderer` uses `UIGraphicsPDFRenderer` with deterministic A4 landscape pages and no network calls. Share a temporary PDF through `ShareLink`; delete the temporary file when the share presentation ends.

- [ ] **Step 4: Run report tests and inspect long-data fixtures**

Run app tests and inspect empty series, 500-point series, warnings, and all-null ECG values.

Expected: tests PASS; charts remain usable and missing values never appear as zero.

- [ ] **Step 5: Commit report and sharing**

```bash
git add ios/LiteRehab/Report ios/LiteRehabTests
git commit -m "feat: add native session reports and PDF sharing"
```

---

### Task 11: Settings, Acknowledgements, and App UI Tests

**Files:**
- Create: `ios/LiteRehab/Settings/SettingsView.swift`
- Create: `ios/LiteRehab/Settings/AcknowledgementsView.swift`
- Create: `ios/LiteRehab/Resources/THIRD_PARTY_NOTICES.md`
- Create: `ios/LiteRehabUITests/PairingFlowTests.swift`
- Create: `ios/LiteRehabUITests/NavigationTests.swift`
- Modify: `ios/LiteRehab/App/AppRootView.swift`

**Interfaces:**
- Consumes: `ConnectionVault`, pairing coordinator, and all three page destinations.
- Produces: rescan/clear connection, prototype information, license presentation, and critical UI coverage.

- [ ] **Step 1: Write failing UI tests with launch arguments**

Use `-ui-testing`, `-fixture-paired`, and `-fixture-empty-history` launch arguments. Test Pairing → scanner cancel, paired Live/History tab navigation, session card → Report, Settings → Acknowledgements, and clear connection → Pairing.

- [ ] **Step 2: Run UI tests and verify missing Settings/accessibility failures**

Run after Xcode install:

```bash
cd ios
xcodebuild -project LiteRehab.xcodeproj -scheme LiteRehab \
  -destination 'platform=iOS Simulator,name=iPhone 16,OS=latest' test
```

Expected: UI tests FAIL until Settings and fixture launch wiring exist.

- [ ] **Step 3: Implement Settings and notices**

Settings displays service name/address, Connected/Reconnecting state, Rescan QR, Clear Connection, API version, engineering-prototype disclaimer, and Acknowledgements. Bundle the full MIT notices for Stanford Spezi and SpeziViews plus repository URLs. Mention CareKit only under design references unless its code becomes a dependency.

- [ ] **Step 4: Run unit/UI tests and accessibility audit**

Run all app tests. Inspect VoiceOver labels for status badges, camera, ECG, charts, session cards, and destructive clear action. Verify Reduce Motion suppresses decorative transitions.

Expected: all tests PASS with no unlabeled critical control.

- [ ] **Step 5: Commit product completion UI**

```bash
git add ios/LiteRehab/Settings ios/LiteRehab/Resources \
  ios/LiteRehabUITests ios/LiteRehab/App/AppRootView.swift
git commit -m "feat: finish iPhone settings and acknowledgements"
```

---

### Task 12: Documentation, Full Regression, and Physical-iPhone Verification

**Files:**
- Modify: `README.md`
- Modify: `README_zh.md`
- Modify: `DEMO_GUIDE.md`
- Modify: `scripts/test_all.sh`
- Modify: `ios/project.yml` only if Xcode verification requires a deterministic setting fix

**Interfaces:**
- Consumes: the completed backend and native app.
- Produces: reproducible setup, one-command regression checks, and physical-device handoff instructions.

- [ ] **Step 1: Add the documented commands to the automated test script**

Add `cd "$ROOT/ios/LiteRehabCore" && swift test` unconditionally. Run Xcode tests only when `xcodebuild -version` succeeds and print an explicit SKIP otherwise; do not report skipped iOS tests as passed.

- [ ] **Step 2: Document installation and demo flow**

Document:

1. install full Xcode and select it with `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer`;
2. install XcodeGen with Homebrew;
3. install Python requirements;
4. generate/open `ios/LiteRehab.xcodeproj`;
5. choose a Personal Team and unique bundle ID if necessary;
6. run `./scripts/start_ios_demo.sh <camera-source>`;
7. scan the terminal QR;
8. trust Developer Mode on each iPhone when prompted; and
9. reinstall after the free seven-day provisioning profile expires.

- [ ] **Step 3: Run the complete non-hardware regression suite**

Run: `./scripts/test_all.sh`

Run: `cd web && npm test -- --run && npm run build`

Run after Xcode install:

```bash
cd ios
xcodegen generate
xcodebuild -project LiteRehab.xcodeproj -scheme LiteRehab \
  -destination 'platform=iOS Simulator,name=iPhone 16,OS=latest' test
```

Expected: Python/C/web/Swift core tests pass, web production build passes, and iOS unit/UI tests pass. Any unavailable hardware test is reported separately.

- [ ] **Step 4: Perform the real-device acceptance checklist**

On the trusted demo Wi-Fi, verify QR pairing, camera frames, live snapshots, ECG, Start, baseline, range reset, Stop, History refresh, Report charts, PDF share, Wi-Fi disconnect/reconnect, invalid-token rescan, and installation on each team iPhone.

Expected: every acceptance criterion in `docs/superpowers/specs/2026-07-20-ios-native-app-design.md` is observed or has a recorded blocker with evidence.

- [ ] **Step 5: Commit final documentation and verification wiring**

```bash
git add README.md README_zh.md DEMO_GUIDE.md scripts/test_all.sh ios/project.yml
git commit -m "docs: add native iPhone demo workflow"
```

---

## Plan Self-Review

- Spec coverage: pairing, authentication, scoped LAN access, three pages, commands, camera, ECG, reports, PDF, errors, acknowledgements, testing, and physical installation each map to a task.
- Scope control: App Store, cloud, HealthKit, direct BLE, direct camera, and on-device inference remain excluded.
- Type consistency: `ServerConnection`, `RequestFactory`, `APIClientProtocol`, `LiveSnapshot`, `SessionSummary`, and `SessionReport` are defined before consumers.
- Verification gap: full Xcode is not currently installed. Tasks 1-5 remain fully executable; Tasks 6-12 require Xcode for final compilation and simulator/device verification.
