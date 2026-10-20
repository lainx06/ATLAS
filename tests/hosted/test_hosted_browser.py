"""T-12 step 4: secrets stay on the server (Playwright against the hosted app; offline).

The app runs in hosted mode under `hosted_server.py` (a mocked Token Factory; loopback-only
networking) with synthetic secret markers and the disposable local PostgreSQL. A signed-out
browser opens the recorded runs and runs one live session on each route (a wrong judge code,
then the correct one, in a fresh browser context each). No secret marker may appear in:

- the page source (the rendered DOM);
- any HTTP response or WebSocket frame the server sends to the browser;
- the server log;
- any file the sessions wrote (logs, reports, replies, proposals) or the events table;
- the bundle.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request

import hosted_helpers as H
import psycopg
import pytest

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def database(postgres_server):
    import secrets

    host, port, user, password = postgres_server
    name = f"b_{secrets.token_hex(6)}"
    admin = f"postgresql://{user}:{password}@{host}:{port}/atlas_test"
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{name}"')
    yield f"postgresql://{user}:{password}@{host}:{port}/{name}", password
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture(scope="module")
def server(tmp_path_factory, database):
    url_db, password = database
    base = tmp_path_factory.mktemp("hosted-app")
    port = _free_port()
    env = {
        **os.environ,
        "ATLAS_HOSTED": "1",
        "ATLAS_HOSTED_RUNS_DIR": str(base / "runs"),
        "NEBIUS_API_KEY": H.KEY,
        "DATABASE_URL": url_db,
        "JUDGE_ACCESS_CODE": H.JUDGE_CODE,
        "HOSTED_LIVE_ENABLED": "true",
        "ATLAS_TEST_PROVIDER_LOG": str(base / "provider.log"),
        "ATLAS_TEST_GUARD_LOG": str(base / "guard.log"),
    }
    log = base / "server.log"
    with open(log, "wb") as out:
        proc = subprocess.Popen(
            [sys.executable, str(H.ROOT / "tests" / "hosted" / "hosted_server.py"), str(port)],
            cwd=H.ROOT, env=env, stdout=out, stderr=subprocess.STDOUT,
        )  # fmt: skip
    url = f"http://localhost:{port}"
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/_stcore/health", timeout=2) as r:
                if r.status == 200:
                    break
        except OSError:
            time.sleep(0.5)
    else:
        proc.kill()
        pytest.fail(f"hosted app did not start; see {log}")
    yield {"url": url, "base": base, "log": log, "db": url_db, "password": password}
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, check=False)  # fmt: skip
    else:
        proc.kill()
    proc.wait(timeout=10)


class Wire:
    """Everything the server sends to one page: HTTP response bodies and WebSocket frames."""

    def __init__(self, page):
        self.chunks: list[bytes] = []
        page.on("response", self._response)
        page.on("websocket", self._socket)

    def _response(self, response):
        try:
            self.chunks.append(response.body())
        except Exception:  # noqa: BLE001, S110 - a redirect or aborted response has no body
            pass

    def _socket(self, ws):
        ws.on("framereceived", self._frame)

    def _frame(self, payload):
        self.chunks.append(payload if isinstance(payload, bytes) else payload.encode())

    def blob(self) -> bytes:
        return b"".join(self.chunks)


def markers(server) -> list[str]:
    """Secrets checked fragment by fragment (the DATABASE_URL by its password, and whole)."""
    return [H.KEY, H.JUDGE_CODE, server["password"]]


FRAGMENT = 10  # any 10 consecutive characters of a marker count as a leak


def fragments(secret: str) -> set[str]:
    n = min(FRAGMENT, len(secret))
    return {secret[i : i + n] for i in range(len(secret) - n + 1)}


def assert_absent(data: bytes | str, server, where: str, *, typed: str | None = None):
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    for marker in [*markers(server), *([typed] if typed else [])]:
        leaked = [f for f in fragments(marker) if f in text]
        assert not leaked, f"a secret marker (or part of it) appeared in {where}"
    assert server["db"] not in text, f"DATABASE_URL appeared in {where}"


def live_session(page, server, typed: str, expected: str):
    wire = Wire(page)
    page.goto(server["url"])
    page.get_by_text("Replay: these are recorded runs", exact=False).wait_for(
        timeout=60_000
    )
    page.locator(".st-key-step-5 summary").first.click()  # step 5: the evidence panel
    page.locator(".st-key-card-integrity").wait_for(timeout=60_000)
    card = page.locator(".st-key-card-integrity").inner_text()
    assert (
        "recorded items verified now (" in card and "matches the files on disk" in card
    )
    shots = H.ROOT / "runs" / "t12" / "screens"  # git-ignored evidence
    shots.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(shots / "hosted_recorded.png"), full_page=True)
    page.get_by_role("link", name="Try It Live").click()  # the navigation
    page.get_by_role("textbox", name="Judge access code (optional)").fill(typed)
    page.get_by_role("button", name="Start the live session").click()
    page.get_by_text(expected, exact=True).wait_for(timeout=180_000)
    page.locator(".st-key-proposal-1").wait_for(timeout=60_000)
    route = "judge" if "judge" in expected else "public"
    page.screenshot(path=str(shots / f"hosted_live_{route}.png"), full_page=True)
    page.locator(".st-key-proposal-hosted-1").screenshot(
        path=str(shots / f"hosted_revision_{route}.png")
    )
    content = page.content()
    assert "not_executed_here" in content and "not executed here" in content
    assert "computed by ATLAS" in content and "(recorded 2026-10-18)" in content
    assert_absent(content, server, "the page source", typed=typed)
    assert_absent(
        wire.blob(), server, "what the server sent to the browser", typed=typed
    )
    assert page.get_by_role("button", name="Start the live session").count() == 0


def test_secrets_stay_on_the_server(server, browser):
    wrong = "wrong-" + H.JUDGE_CODE[6:]
    for typed, expected in (
        (wrong, "Route: public demo budget."),
        (H.JUDGE_CODE, "Route: judge pool (access code accepted)."),
    ):
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        try:
            live_session(context.new_page(), server, typed, expected)
        finally:
            context.close()

    base = server["base"]
    posts = (base / "provider.log").read_text(encoding="utf-8").split()
    assert len(posts) == 8  # two sessions, four requests each, all to the mock
    assert (base / "guard.log").read_text(encoding="utf-8") == ""  # loopback only
    assert_absent(server["log"].read_bytes(), server, "the server log", typed=wrong)
    written = [p for p in (base / "runs").rglob("*") if p.is_file()]
    assert len([p for p in written if p.name == "agent_report.json"]) == 2
    for path in written:
        assert_absent(path.read_bytes(), server, f"run file {path.name}", typed=wrong)
    with psycopg.connect(server["db"], autocommit=True) as conn:
        dump = str(
            [conn.execute(f"SELECT * FROM {t}").fetchall()
             for t in ("atlas_event", "atlas_cap", "atlas_reservation")]
        )  # fmt: skip
        events = conn.execute(
            "SELECT route, event FROM atlas_event ORDER BY id"
        ).fetchall()
    assert_absent(dump, server, "the budget store", typed=wrong)
    assert ("judge", "judge_code_rejected") in events
    assert ("judge", "judge_code_accepted") in events
    for path in H.BUNDLE.rglob("*"):
        if path.is_file():
            assert_absent(path.read_bytes(), server, f"bundle file {path.name}")
