# LiteRehab Local Web Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished offline browser application that preserves LiteRehab's existing hardware and inference pipeline while adding live training, session history, and printable reports.

**Architecture:** A reusable Python runtime service owns serial, camera, pose, inference, synchronization, and CSV recording. FastAPI exposes REST, WebSocket, and MJPEG interfaces. A React/Vite/TypeScript frontend renders three focused pages and is served locally by FastAPI after production build.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, OpenCV, existing LiteRehab modules, React 19, TypeScript, Vite, Tailwind CSS, Radix primitives, Lucide icons, Recharts, Vitest, Testing Library.

## Global Constraints

- The application must run on one laptop at `127.0.0.1` without internet, accounts, a cloud database, or external APIs.
- Preserve current ESP32-S3 telemetry, MaixCAM2 camera, MediaPipe pose, IMU inference, fusion rules, and CSV schemas.
- Existing CSV and companion ECG CSV files remain authoritative session data.
- The live page must fit at 1280 x 720 without vertical scrolling.
- Do not show invented rehabilitation scores, diagnostic ECG interpretation, fake goals, or unavailable measurements as zero.
- Avoid gradient text, glassmorphism, glowing borders, decorative blobs, oversized repeated cards, fake percentage KPIs, and gratuitous animation.
- Keep the existing OpenCV dashboard available during migration.

---

## Planned File Structure

- `python/literehab/session_repository.py`: discover CSV pairs and derive reproducible session/report metrics.
- `python/literehab/web_models.py`: immutable live snapshot and API response models.
- `python/literehab/web_runtime.py`: runtime command interface, fixture runtime, and real acquisition engine.
- `python/literehab/web_app.py`: FastAPI application factory, REST, WebSocket, MJPEG, and static frontend hosting.
- `python/run_web_dashboard.py`: local launcher and browser opening.
- `python/tests/test_session_repository.py`: derived metric and malformed-input coverage.
- `python/tests/test_web_app.py`: API, WebSocket, and stream tests with fixture runtime.
- `python/tests/test_web_runtime.py`: command and bounded-state tests.
- `web/`: Vite/React application.
- `web/src/app/`: router, shell, API client, and shared live connection hook.
- `web/src/features/live/`: live training page and bounded ECG buffer.
- `web/src/features/history/`: session list, filters, and completeness states.
- `web/src/features/report/`: report detail, charts, disclaimer, and print layout.
- `scripts/start_web_demo.sh`: build-if-needed and start the local application.

### Task 1: Session Repository and Report Metrics

**Files:**
- Create: `python/literehab/session_repository.py`
- Create: `python/tests/test_session_repository.py`

**Interfaces:**
- Produces: `SessionRepository(root: Path)`, `SessionSummary`, `SessionReport`, `list_sessions() -> list[SessionSummary]`, and `get_report(session_id: str) -> SessionReport`.
- Consumes: the existing `SESSION_FIELDS` CSV and `<stem>_ecg.csv` companion format.

- [ ] **Step 1: Write failing tests for reproducible metrics**

```python
def test_report_derives_events_without_counting_repeated_rows(tmp_path):
    write_session(tmp_path / "demo.csv", [
        row(1.0, "idle", 0, "none", elbow=40),
        row(2.0, "elbow_flexion", 1, "ok", elbow=85),
        row(3.0, "elbow_flexion", 1, "ok", elbow=100),
        row(4.0, "elbow_flexion", 2, "too_fast", elbow=70),
    ])
    report = SessionRepository(tmp_path).get_report("demo")
    assert report.duration_s == 3.0
    assert report.repetitions == 2
    assert report.quality_counts == {"ok": 1, "too_fast": 1}
    assert report.good_form_percent == 50.0
    assert report.max_rom_deg == 60.0
```

- [ ] **Step 2: Run the focused test and verify the missing-module failure**

Run: `PYTHONPATH=python pytest python/tests/test_session_repository.py -q`

Expected: collection fails with `ModuleNotFoundError: literehab.session_repository`.

- [ ] **Step 3: Implement defensive CSV discovery and metric derivation**

```python
class SessionRepository:
    def __init__(self, root: Path):
        self.root = root

    def list_sessions(self) -> list[SessionSummary]:
        reports = [self._parse(path) for path in self._session_paths()]
        return [report.to_summary() for report in reports]

    def get_report(self, session_id: str) -> SessionReport:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", session_id):
            raise KeyError(session_id)
        path = self.root / f"{session_id}.csv"
        if not path.is_file() or path.name.endswith("_ecg.csv"):
            raise KeyError(session_id)
        return self._parse(path)
```

Implement positive `rep_count` increments, distinct quality transitions,
valid-pose intervals, connected positive BPM averaging, and separate pose/ECG
completeness. Invalid cells add data-quality warnings and yield `None` for
unreliable metrics.

- [ ] **Step 4: Run repository tests**

Run: `PYTHONPATH=python pytest python/tests/test_session_repository.py -q`

Expected: all repository tests pass.

- [ ] **Step 5: Commit the repository unit**

```bash
git add python/literehab/session_repository.py python/tests/test_session_repository.py
git commit -m "feat: derive local session reports"
```

### Task 2: Web Models, Fixture Runtime, and FastAPI Contract

**Files:**
- Modify: `python/requirements.txt`
- Create: `python/literehab/web_models.py`
- Create: `python/literehab/web_runtime.py`
- Create: `python/literehab/web_app.py`
- Create: `python/tests/test_web_runtime.py`
- Create: `python/tests/test_web_app.py`

**Interfaces:**
- Consumes: `SessionRepository` from Task 1.
- Produces: `LiveSnapshot.to_dict()`, `RuntimeProtocol`, `FixtureRuntime`, and `create_app(runtime, sessions_dir, frontend_dir=None) -> FastAPI`.

- [ ] **Step 1: Add failing contract tests**

```python
def test_live_snapshot_distinguishes_unavailable_values():
    snapshot = LiveSnapshot.initial()
    assert snapshot.rom_deg is None
    assert snapshot.ecg_bpm is None
    assert snapshot.serial_status == "unavailable"

def test_api_lists_sessions_and_controls_runtime(tmp_path):
    runtime = FixtureRuntime()
    client = TestClient(create_app(runtime, tmp_path))
    assert client.get("/api/sessions").status_code == 200
    response = client.post("/api/session/start", json={"subject": "Demo-01"})
    assert response.status_code == 200
    assert runtime.recording is True
```

- [ ] **Step 2: Run tests and verify missing symbols**

Run: `PYTHONPATH=python pytest python/tests/test_web_runtime.py python/tests/test_web_app.py -q`

Expected: import failures for `web_models`, `web_runtime`, and `web_app`.

- [ ] **Step 3: Add exact backend dependencies**

Append to `python/requirements.txt`:

```text
fastapi>=0.116,<1
uvicorn[standard]>=0.35,<1
httpx>=0.28,<1
```

- [ ] **Step 4: Implement runtime protocol and bounded fixture state**

```python
class RuntimeProtocol(Protocol):
    recording: bool
    def snapshot(self) -> LiveSnapshot: ...
    def start_session(self, subject: str) -> None: ...
    def stop_session(self) -> None: ...
    def recapture_baseline(self) -> None: ...
    def reset_range(self) -> None: ...
    def jpeg_frame(self) -> bytes | None: ...

class FixtureRuntime:
    def __init__(self) -> None:
        self.recording = False
        self.subject = ""
        self._snapshot = LiveSnapshot.initial()
```

- [ ] **Step 5: Implement API routes and streams**

```python
@app.get("/api/sessions")
def sessions() -> list[dict[str, object]]:
    return [asdict(item) for item in repository.list_sessions()]

@app.websocket("/api/live")
async def live(socket: WebSocket) -> None:
    await socket.accept()
    try:
        while True:
            await socket.send_json(runtime.snapshot().to_dict())
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        return
```

Add exact 404 mapping for unknown reports, 409 mapping for invalid session
transitions, subject trimming/length validation, and a multipart MJPEG response.

- [ ] **Step 6: Run backend contract tests**

Run: `PYTHONPATH=python pytest python/tests/test_session_repository.py python/tests/test_web_runtime.py python/tests/test_web_app.py -q`

Expected: all tests pass.

- [ ] **Step 7: Commit the API unit**

```bash
git add python/requirements.txt python/literehab/web_models.py python/literehab/web_runtime.py python/literehab/web_app.py python/tests/test_web_runtime.py python/tests/test_web_app.py
git commit -m "feat: add local dashboard API"
```

### Task 3: React Application Shell and Product Visual System

**Files:**
- Create: `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/index.html`
- Create: `web/src/main.tsx`, `web/src/styles.css`
- Create: `web/src/app/App.tsx`, `web/src/app/AppShell.tsx`, `web/src/app/api.ts`
- Create: `web/src/app/App.test.tsx`, `web/src/test/setup.ts`

**Interfaces:**
- Consumes: REST paths under `/api` from Task 2.
- Produces: route shell for `/`, `/history`, and `/reports/:sessionId`; shared `StatusPill`, `Metric`, `EmptyState`, and `PageHeader` components.

- [ ] **Step 1: Scaffold Vite dependencies and failing navigation test**

```tsx
it("renders the three product destinations", () => {
  render(<App />)
  expect(screen.getByRole("link", { name: /live training/i })).toBeVisible()
  expect(screen.getByRole("link", { name: /session history/i })).toBeVisible()
  expect(screen.queryByText(/upgrade plan/i)).not.toBeInTheDocument()
})
```

- [ ] **Step 2: Run the frontend test and verify failure**

Run: `cd web && npm install && npm test -- --run`

Expected: failure because `App` and the shell do not exist.

- [ ] **Step 3: Implement the restrained application shell**

```tsx
const navigation = [
  { to: "/", label: "Live Training", icon: Activity },
  { to: "/history", label: "Session History", icon: History },
]
```

Use CSS variables for navy, paper, surface, teal, green, amber, red, border,
and muted text. Use an 80px collapsed/224px expanded rail, 1px borders, 10px
card radius, tabular numerals, no gradients, and no shadow stronger than
`0 1px 2px rgb(15 23 42 / 0.06)`.

- [ ] **Step 4: Run shell tests and production build**

Run: `cd web && npm test -- --run && npm run build`

Expected: tests pass and `web/dist/index.html` is generated.

- [ ] **Step 5: Commit the frontend foundation**

```bash
git add web
git commit -m "feat: add rehabilitation web shell"
```

### Task 4: Live Training Page

**Files:**
- Create: `web/src/app/useLiveSnapshot.ts`
- Create: `web/src/features/live/LivePage.tsx`
- Create: `web/src/features/live/EcgTrace.tsx`
- Create: `web/src/features/live/liveBuffer.ts`
- Create: `web/src/features/live/LivePage.test.tsx`
- Create: `web/src/features/live/liveBuffer.test.ts`

**Interfaces:**
- Consumes: WebSocket `/api/live`, camera `/api/camera.mjpg`, and session command endpoints.
- Produces: complete no-scroll live view and `appendBounded<T>(items, item, limit)`.

- [ ] **Step 1: Write failing state and buffer tests**

```tsx
it("shows unavailable ECG without inventing zero BPM", () => {
  render(<LivePage snapshot={{ ...initialSnapshot, ecgConnected: false, ecgBpm: null }} />)
  expect(screen.getByText("Leads off")).toBeVisible()
  expect(screen.queryByText("0 BPM")).not.toBeInTheDocument()
})

it("bounds live samples", () => {
  expect(appendBounded([1, 2], 3, 2)).toEqual([2, 3])
})
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `cd web && npm test -- --run src/features/live`

Expected: missing component/helper failures.

- [ ] **Step 3: Implement reconnecting live state and command actions**

```ts
export function appendBounded<T>(items: T[], item: T, limit: number): T[] {
  return [...items, item].slice(-limit)
}
```

The page grid is camera `minmax(0, 1fr)`, metrics `280px`, and ECG `150px`
high. Use semantic status text plus icons. Start session requires a participant
ID; stop asks for confirmation; baseline and range controls remain secondary.

- [ ] **Step 4: Run live tests and build**

Run: `cd web && npm test -- --run src/features/live && npm run build`

Expected: tests and build pass.

- [ ] **Step 5: Commit the live page**

```bash
git add web/src/app/useLiveSnapshot.ts web/src/features/live
git commit -m "feat: add live rehabilitation view"
```

### Task 5: Session History and Printable Report

**Files:**
- Create: `web/src/features/history/HistoryPage.tsx`
- Create: `web/src/features/history/filterSessions.ts`
- Create: `web/src/features/history/HistoryPage.test.tsx`
- Create: `web/src/features/report/ReportPage.tsx`
- Create: `web/src/features/report/ReportCharts.tsx`
- Create: `web/src/features/report/ReportPage.test.tsx`
- Modify: `web/src/styles.css`

**Interfaces:**
- Consumes: `GET /api/sessions` and `GET /api/sessions/:sessionId`.
- Produces: searchable session table, report route, and print/PDF stylesheet.

- [ ] **Step 1: Write failing history and report tests**

```tsx
it("filters sessions by participant and exercise", () => {
  expect(filterSessions(fixtures, { query: "demo-02", exercise: "elbow_flexion" }))
    .toHaveLength(1)
})

it("prints the prototype disclaimer and unavailable values", () => {
  render(<ReportPage report={{ ...report, averageBpm: null }} />)
  expect(screen.getByText(/not a medical device/i)).toBeVisible()
  expect(screen.getByText("Not available")).toBeVisible()
})
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `cd web && npm test -- --run src/features/history src/features/report`

Expected: missing feature failures.

- [ ] **Step 3: Implement real filtering, completeness, charts, and print CSS**

```css
@media print {
  .app-sidebar, .no-print { display: none !important; }
  .app-main { margin: 0; padding: 0; }
  .report-page { color: #0f172a; background: #fff; }
  @page { size: A4 landscape; margin: 12mm; }
}
```

Do not place all metrics in identical cards. Use a compact table for sessions,
a four-column summary strip for the report, and larger chart panels only where
time-series shape matters. Render missing values as `Not available` with a
data-quality explanation.

- [ ] **Step 4: Run feature tests and build**

Run: `cd web && npm test -- --run src/features/history src/features/report && npm run build`

Expected: tests and build pass.

- [ ] **Step 5: Commit history and reports**

```bash
git add web/src/features/history web/src/features/report web/src/styles.css
git commit -m "feat: add session history and reports"
```

### Task 6: Real LiteRehab Runtime Integration

**Files:**
- Modify: `python/literehab/web_runtime.py`
- Modify: `python/run_dashboard.py`
- Create: `python/tests/test_real_web_runtime.py`

**Interfaces:**
- Consumes: existing `SerialReader`, `OptionalCNN`, camera, pose, synchronization, fusion, dashboard state, and CSV field definitions.
- Produces: `LiteRehabRuntime(RuntimeProtocol)` with `start()`, `close()`, command methods, immutable snapshots, and JPEG frames.

- [ ] **Step 1: Write failing lifecycle and command tests with injected fakes**

```python
def test_session_commands_open_and_close_both_csv_files(tmp_path):
    runtime = LiteRehabRuntime(RuntimeConfig(sessions_dir=tmp_path), sources=FakeSources())
    runtime.start_session("Demo-01")
    assert runtime.recording
    runtime.stop_session()
    assert not runtime.recording
    assert len(list(tmp_path.glob("*.csv"))) == 2
```

- [ ] **Step 2: Run runtime tests and verify failure**

Run: `PYTHONPATH=python pytest python/tests/test_real_web_runtime.py -q`

Expected: `LiteRehabRuntime` or injected source interfaces are missing.

- [ ] **Step 3: Extract orchestration behind the runtime boundary**

```python
@dataclass(frozen=True)
class RuntimeConfig:
    port: str = "auto"
    camera_source: int | str = 0
    side: str = "right"
    sessions_dir: Path = Path("python/sessions")
    model: Path | None = None
    fusion_model: Path | None = None
    model_confidence: float = 0.70
```

Use one worker thread, a lock-protected immutable snapshot, bounded telemetry
deques, and an event for shutdown. Open CSV writers only during a session.
Reuse existing algorithms and parsing; do not duplicate feedback rules in the
web layer. `run_dashboard.py` keeps its CLI and current OpenCV behavior.

- [ ] **Step 4: Run runtime and existing dashboard tests**

Run: `PYTHONPATH=python pytest python/tests/test_real_web_runtime.py python/tests/test_dashboard_cli.py python/tests/test_dashboard_state.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit real runtime integration**

```bash
git add python/literehab/web_runtime.py python/run_dashboard.py python/tests/test_real_web_runtime.py
git commit -m "feat: connect web dashboard to LiteRehab runtime"
```

### Task 7: Launcher, Documentation, and Full Verification

**Files:**
- Create: `python/run_web_dashboard.py`
- Create: `scripts/start_web_demo.sh`
- Modify: `README.md`
- Modify: `README_zh.md`
- Modify: `DEMO_GUIDE.md`
- Modify: `.gitignore`
- Modify: `python/tests/test_web_app.py`

**Interfaces:**
- Consumes: `create_app`, `LiteRehabRuntime`, and `web/dist`.
- Produces: one-command offline demo and documented fallback behavior.

- [ ] **Step 1: Write failing launcher/static-hosting test**

```python
def test_built_frontend_falls_back_to_spa_routes(tmp_path):
    (tmp_path / "index.html").write_text("<main>LiteRehab</main>")
    client = TestClient(create_app(FixtureRuntime(), Path("missing"), tmp_path))
    assert "LiteRehab" in client.get("/history").text
```

- [ ] **Step 2: Run the launcher test and verify failure**

Run: `PYTHONPATH=python pytest python/tests/test_web_app.py -q`

Expected: `/history` returns 404 before SPA fallback is added.

- [ ] **Step 3: Implement launcher and start script**

```python
def main() -> None:
    args = build_parser().parse_args()
    runtime = LiteRehabRuntime(config_from_args(args))
    runtime.start()
    webbrowser.open(f"http://{args.host}:{args.port}")
    uvicorn.run(create_app(runtime, args.sessions_dir, args.frontend_dir),
                host=args.host, port=args.port)
```

`scripts/start_web_demo.sh` builds `web/dist` only when it is missing or older
than `web/src`, sets `PYTHONPATH=python`, and executes the launcher with the
same port, camera source, side, and model defaults as the existing demo script.

- [ ] **Step 4: Document offline startup and safety boundaries**

Add exact install, build, start, navigation, browser-print, IMU-only fallback,
and shutdown commands to English and Chinese READMEs and the demo guide.

- [ ] **Step 5: Run complete verification**

Run:

```bash
./scripts/test_all.sh
cd web && npm test -- --run && npm run build
cd .. && PYTHONPATH=python pytest python/tests -q
PYTHONPATH=python python python/run_web_dashboard.py --fixture --headless-smoke-test
```

Expected: C tests, all Python tests, all frontend tests, frontend build, and the
headless web smoke test pass.

- [ ] **Step 6: Commit launcher and documentation**

```bash
git add python/run_web_dashboard.py scripts/start_web_demo.sh README.md README_zh.md DEMO_GUIDE.md .gitignore python/tests/test_web_app.py
git commit -m "feat: ship offline LiteRehab web demo"
```

