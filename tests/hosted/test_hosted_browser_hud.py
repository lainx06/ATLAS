"""UI design pass phase 2 in the browser, hosted mode (offline; parts B, C and E).

The app runs under `hosted_server.py` (mocked Token Factory, loopback-only networking) with the
disposable local PostgreSQL and synthetic secrets. Each mocked request is held for a moment
(`ATLAS_TEST_POST_DELAY_S`), so the page can be seen while the session is still going: the
mission track shows the stages recorded so far and lights the new ones, the gauge the
requests so far; at the end the finished session shows its briefing (with "Proposals were
checked by ATLAS validation and not executed here."), the Route line, the proposal in the
model-written frame and its full track. A second server answers every session with the
store's refusal: the BUDGET_EXHAUSTED state. With ATLAS_UI_SCREENS set, the states are saved
at three sizes, with frames and a video of the track's progression.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import hosted_helpers as H
import psycopg
import pytest

sys.path.insert(0, str(H.ROOT / "tests" / "acceptance"))
from helpers import settle, shots

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def database(postgres_server):
    import secrets

    host, port, user, password = postgres_server
    name = f"u_{secrets.token_hex(6)}"
    admin = f"postgresql://{user}:{password}@{host}:{port}/atlas_test"
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{name}"')
    yield f"postgresql://{user}:{password}@{host}:{port}/{name}"
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


def start(base: Path, database: str, **extra) -> tuple[str, subprocess.Popen]:
    port = _free_port()
    env = {
        **os.environ,
        "ATLAS_HOSTED": "1",
        "ATLAS_HOSTED_RUNS_DIR": str(base / "runs"),
        "NEBIUS_API_KEY": H.KEY,
        "DATABASE_URL": database,
        "JUDGE_ACCESS_CODE": H.JUDGE_CODE,
        "HOSTED_LIVE_ENABLED": "true",
        "ATLAS_TEST_PROVIDER_LOG": str(base / "provider.log"),
        "ATLAS_TEST_GUARD_LOG": str(base / "guard.log"),
        **extra,
    }
    with open(base / "server.log", "wb") as out:
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
                    return url, proc
        except OSError:
            time.sleep(0.5)
    proc.kill()
    pytest.fail(f"hosted app did not start; see {base / 'server.log'}")


def stop(proc: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, check=False)  # fmt: skip
    else:
        proc.kill()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def slow(tmp_path_factory, database):
    base = tmp_path_factory.mktemp("hosted-hud")
    url, proc = start(base, database, ATLAS_TEST_POST_DELAY_S="2.5")
    yield url
    stop(proc)


@pytest.fixture(scope="module")
def exhausted(tmp_path_factory, database):
    base = tmp_path_factory.mktemp("hosted-exhausted")
    url, proc = start(base, database, ATLAS_TEST_EXHAUSTED="1")
    yield url
    stop(proc)


def to_live(page, url: str) -> None:
    page.goto(url)
    page.locator(".st-key-card-integrity").wait_for(timeout=60_000)
    page.get_by_test_id("stSidebar").get_by_text("Live session", exact=True).click()
    page.get_by_role("button", name="Start the live session").wait_for(timeout=60_000)


def stages(page) -> int:
    return page.locator(".st-key-hud-track li.hud-stage").count()


def test_the_live_track_follows_a_session_in_the_browser(slow, browser):
    folder = os.environ.get("ATLAS_UI_SCREENS")
    video = (
        {"record_video_dir": str(Path(folder) / "video_hosted_live_track")}
        if folder
        else {}
    )
    context = browser.new_context(viewport={"width": 1440, "height": 900}, **video)
    page = context.new_page()
    to_live(page, slow)
    shots(page, "p2_40_hosted_live_start")
    page.get_by_role("button", name="Start the live session").click()
    track = page.locator(".st-key-hud-track")
    track.wait_for(timeout=60_000)
    # While the session runs: the latest stage is current, the gauge counts against 6.
    page.locator(".st-key-hud-track [aria-current='step']").wait_for(timeout=60_000)
    assert page.locator(".st-key-route").count() == 0
    gauge = page.locator(".st-key-hud-gauge").inner_text()
    assert "of 6" in gauge and "estimate cap" in gauge
    seen = [stages(page)]
    shots(page, "p2_41_live_track_intermediate", track)  # the session is still going
    frames = 0
    deadline = time.time() + 120
    while time.time() < deadline and page.locator(".st-key-route").count() == 0:
        n = stages(page)
        if n != seen[-1]:
            seen.append(n)
            if folder and frames < 6:
                page.screenshot(
                    path=str(
                        Path(folder) / f"p2_41_live_track_frame{frames}_1440x900.png"
                    )
                )
                frames += 1
        time.sleep(0.25)
    assert len(seen) >= 3, seen  # the track grew while the session ran
    assert seen == sorted(seen)
    page.locator(".st-key-route").wait_for(timeout=120_000)
    page.locator(".st-key-hud-briefing").wait_for(timeout=60_000)
    brief = page.locator(".st-key-hud-briefing").inner_text()
    assert "Proposals were checked by ATLAS validation and not executed here." in brief
    assert "Live session in progress" not in page.locator("body").inner_text()
    final = stages(page)
    assert final >= seen[-1]
    assert page.locator(".st-key-hud-track [aria-current='step']").count() == 0
    settle(page)
    shots(page, "p2_42_hosted_briefing_final", page.locator(".st-key-hud-briefing"))
    shots(page, "p2_43_hosted_track_final", track)
    shots(page, "p2_44_hosted_proposal_frame", page.locator(".st-key-proposal-1"))
    frame = page.locator(".st-key-model-diff-1")
    assert "MODEL-WRITTEN · UNTRUSTED" in frame.inner_text()
    assert "not executed here" in page.locator(".st-key-proposal-1").inner_text()
    context.close()


def test_an_exhausted_budget_is_a_state(exhausted, page):
    to_live(page, exhausted)
    page.get_by_role("button", name="Start the live session").click()
    state = page.locator(".st-key-live-exhausted")
    state.wait_for(timeout=60_000)
    shown = state.inner_text()
    assert "BUDGET_EXHAUSTED" in shown and "Live demo budget reached for today" in shown
    assert "Next action:" in shown
    shots(page, "p2_45_hosted_budget_exhausted", state)
