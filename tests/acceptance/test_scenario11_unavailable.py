"""Scenario 11 (UI design pass, phase 2): honest-empty states without Docker or recorded runs.

The app server's Docker CLI points at a daemon that is not there (DOCKER_HOST on a closed
loopback port; this server only, nothing else is touched) and its recorded-run folder is
empty. The claim card shows the amber Docker-unavailable state with its reason and next
action, and agent runs never fall back to the host; the recorded view shows "no recorded
runs" with its next action. With ATLAS_UI_SCREENS set, both are saved at three sizes.
"""

from pathlib import Path

from helpers import open_app, select_mode, select_project, shots, wait_idle


def app_env(base: Path) -> dict:
    (base / "empty").mkdir()
    return {
        "DOCKER_HOST": "tcp://127.0.0.1:9",
        "ATLAS_UI_RECORDED_DIR": str(base / "empty"),
    }


def test_docker_unavailable_is_a_state_with_a_next_action(app, page):
    open_app(page, app)
    select_project(page, "s01_faulty")
    select_mode(page, "Agent, fixture replies (NON-LIVE)")
    state = page.locator("[class*='st-key-state-amber-docker']")
    state.wait_for(timeout=30_000)
    shown = state.inner_text()
    assert "Docker:" in shown and "never falls back" in shown
    assert "Next action: start Docker, then reload this page." in shown
    assert state.evaluate("e => getComputedStyle(e).borderLeftColor") == (
        "rgb(251, 191, 36)"  # amber, next to the printed state
    )
    assert "Docker:" in page.get_by_test_id("stSidebar").inner_text()
    shots(page, "p2_30_state_docker_unavailable", state)


def test_no_recorded_runs_is_a_state_with_a_next_action(app, page):
    open_app(page, app)
    page.get_by_test_id("stSidebar").get_by_text(
        "Open a recorded run", exact=True
    ).click()
    state = page.locator("[class*='st-key-state-stone-no-runs']")
    state.wait_for(timeout=30_000)
    wait_idle(page)
    shown = state.inner_text()
    assert "NO RECORDED RUNS" in shown and "No finished runs under" in shown
    assert "Next action:" in shown
    shots(page, "p2_31_state_no_recorded_runs", state)
